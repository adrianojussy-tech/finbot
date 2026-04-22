import os
import logging
from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from app.parser import interpretar_mensagem, extrair_valor
from app.database import (inicializar_banco, buscar_usuario, criar_usuario,
    atualizar_nome, salvar_gasto, buscar_resumo, deletar_ultimo_gasto,
    buscar_ultimo_gasto, listar_todos_usuarios, buscar_todos_gastos)
from app.relatorios import gerar_planilha_base64
from app.categorias import detectar_categoria, listar_categorias
from app.orcamento import (inicializar_orcamentos, definir_orcamento,
    verificar_alerta, gasto_categoria_mes, relatorio_orcamentos, remover_orcamento)
from app.agendador import iniciar_scheduler

load_dotenv()
logging.basicConfig(level=logging.INFO)
app = FastAPI(title="FinBot v3")
ESTADO: dict = {}

@app.on_event("startup")
def startup():
    inicializar_banco()
    inicializar_orcamentos()
    iniciar_scheduler()

@app.get("/")
def root():
    return {"status": "FinBot v3 rodando ✅"}

@app.post("/webhook")
def webhook(From: str = Form(...), Body: str = Form(...)):
    numero  = From.strip()
    mensagem = Body.strip()
    resposta = processar(numero, mensagem)
    twiml = MessagingResponse()
    twiml.message(resposta)
    return Response(content=str(twiml), media_type="application/xml")

def processar(numero, mensagem):
    usuario = buscar_usuario(numero)

    if usuario is None:
        criar_usuario(numero)
        ESTADO[numero] = "aguardando_nome"
        return "👋 Olá! Bem-vindo ao *FinBot*! 💰\n\nQual é o seu nome?"

    nome = usuario.get("nome") or "amigo"

    if ESTADO.get(numero) == "aguardando_nome":
        nome = mensagem.strip().title()
        atualizar_nome(numero, nome)
        ESTADO.pop(numero, None)
        return (f"Prazer, *{nome}*! 🎉\n\nRegistre seus gastos assim:\n"
                "• _Gastei 50 reais no mercado_\n• _Uber 22 ontem_\n\nDigite *ajuda* para ver todos os comandos.")

    if ESTADO.get(numero) == "confirmar_exclusao":
        ESTADO.pop(numero, None)
        if mensagem.lower().strip() in ["sim", "s", "yes", "ok"]:
            deletar_ultimo_gasto(numero)
            return f"✅ Último gasto removido, {nome}!"
        return f"👍 Ok, {nome}. Nenhum gasto foi removido."

    ml = mensagem.lower().strip()

    if any(c in ml for c in ["resumo", "total", "quanto gastei"]):
        d = buscar_resumo(numero)
        return (f"📊 *Resumo de {nome}:*\n\n"
                f"📆 Hoje: R$ {d['hoje']:.2f}\n"
                f"📅 Semana: R$ {d['semana']:.2f}\n"
                f"🗓️ Mês: R$ {d['mes']:.2f}\n\n"
                f"_Digite 'grafico' ou 'relatorio' para mais detalhes._")

    if any(c in ml for c in ["relatorio", "relatório", "planilha", "exportar"]):
        csv = gerar_planilha_base64(numero)
        return f"📄 *Relatório de {nome}:*\n\n```\n{csv}\n```" if csv else f"📭 Nenhum gasto ainda, {nome}."

    if any(c in ml for c in ["grafico", "gráfico", "categorias"]):
        from collections import defaultdict
        from datetime import date
        gastos = buscar_todos_gastos(numero)
        mes = [g for g in gastos if str(g["data"])[:7] == date.today().strftime("%Y-%m")]
        if not mes:
            return f"📭 Nenhum gasto este mês, {nome}."
        totais = defaultdict(float)
        for g in mes:
            totais[g["categoria"]] += float(g["valor"])
        total = sum(totais.values())
        linhas = [f"📊 *Gastos de {nome} por categoria:*\n"]
        for cat, val in sorted(totais.items(), key=lambda x: -x[1]):
            pct = (val / total) * 100
            barra = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            linhas.append(f"*{cat}*\n{barra} {pct:.1f}%\nR$ {val:.2f}\n")
        linhas.append(f"💰 *Total: R$ {total:.2f}*")
        return "\n".join(linhas)

    if any(c in ml for c in ["desfazer", "cancelar", "apagar ultimo"]):
        u = buscar_ultimo_gasto(numero)
        if not u:
            return f"📭 Nenhum gasto para desfazer, {nome}."
        ESTADO[numero] = "confirmar_exclusao"
        p = str(u["data"]).split("-")
        return (f"🗑️ Desfazer este gasto?\n\n"
                f"📅 {p[2]}/{p[1]}/{p[0]}\n"
                f"📝 {u['descricao']}\n"
                f"🏷️ {u['categoria']}\n"
                f"💰 R$ {float(u['valor']):.2f}\n\n"
                f"Responda *sim* ou *nao*.")

    if any(c in ml for c in ["ver orcamento", "meu orcamento", "limites"]):
        return relatorio_orcamentos(numero)

    if ml.startswith("orcamento") or ml.startswith("orçamento"):
        cat = next((c for c in listar_categorias() if c.lower() in ml), None)
        if not cat:
            return f"❓ Categoria não reconhecida.\nOpções: {', '.join(listar_categorias())}"
        if "remover" in ml or "excluir" in ml:
            remover_orcamento(numero, cat)
            return f"🗑️ Orçamento de *{cat}* removido, {nome}."
        val = extrair_valor(mensagem)
        if not val:
            return "❓ Informe o valor. Ex: _orcamento Alimentacao 500_"
        definir_orcamento(numero, cat, val)
        return f"✅ Orçamento definido!\n🏷️ {cat}\n💰 R$ {val:.2f}/mês\n\nAlerta em 80% e 100%."

    if any(c in ml for c in ["mudar nome", "trocar nome", "meu nome"]):
        ESTADO[numero] = "aguardando_nome"
        return f"Qual será seu novo nome, {nome}?"

    if any(c in ml for c in ["ajuda", "help", "comandos"]):
        return (f"🤖 *FinBot — Olá, {nome}!*\n\n"
                "💬 *Registrar gasto:*\n"
                "• Gastei 50 no mercado\n"
                "• Uber 22 ontem\n"
                "• Almoco 35,00\n\n"
                "📊 _resumo_ — totais\n"
                "📊 _grafico_ — por categoria\n"
                "📄 _relatorio_ — exportar\n"
                "💳 _orcamento Alimentacao 500_\n"
                "↩️ _desfazer_ — remove último\n"
                "✏️ _mudar nome_")

    gasto = interpretar_mensagem(mensagem)
    if gasto:
        if gasto["categoria"] == "Outros":
            gasto["categoria"] = detectar_categoria(mensagem)
        salvar_gasto(numero, gasto)
        total_cat = gasto_categoria_mes(numero, gasto["categoria"])
        alerta = verificar_alerta(numero, gasto["categoria"], total_cat)
        p = gasto["data"].split("-")
        resp = (f"✅ *Registrado, {nome}!*\n\n"
                f"📅 {p[2]}/{p[1]}/{p[0]}\n"
                f"📝 {gasto['descricao']}\n"
                f"🏷️ {gasto['categoria']}\n"
                f"💰 R$ {gasto['valor']:.2f}")
        if alerta:
            resp += f"\n\n{alerta}"
        return resp

    return (f"❓ Não entendi, {nome}.\n\nExemplos:\n"
            "• _Gastei 50 no mercado_\n"
            "• _Uber 22_\n\nDigite *ajuda*.")