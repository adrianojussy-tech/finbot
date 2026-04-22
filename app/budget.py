from datetime import date
from app.database import get_conn
from app.categories import listar_categorias

def inicializar_orcamentos():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS orcamentos (
            id SERIAL PRIMARY KEY, numero TEXT NOT NULL,
            categoria TEXT NOT NULL, limite NUMERIC(10,2) NOT NULL,
            UNIQUE(numero,categoria))""")
        conn.commit()

def definir_orcamento(numero, categoria, limite):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO orcamentos(numero,categoria,limite) VALUES(%s,%s,%s) ON CONFLICT(numero,categoria) DO UPDATE SET limite=EXCLUDED.limite",
            (numero, categoria, limite))
        conn.commit()

def buscar_orcamentos(numero):
    with get_conn() as conn:
        cur = conn.execute("SELECT categoria,limite FROM orcamentos WHERE numero=%s", (numero,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

def remover_orcamento(numero, categoria):
    with get_conn() as conn:
        conn.execute("DELETE FROM orcamentos WHERE numero=%s AND categoria=%s", (numero, categoria))
        conn.commit()

def gasto_categoria_mes(numero, categoria):
    ini = date.today().replace(day=1).isoformat()
    fim = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(valor),0) FROM gastos WHERE numero=%s AND categoria=%s AND data BETWEEN %s AND %s",
            (numero, categoria, ini, fim)).fetchone()
        return float(row[0])

def verificar_alerta(numero, categoria, gasto_mes):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT limite FROM orcamentos WHERE numero=%s AND categoria=%s",
            (numero, categoria)).fetchone()
    if not row:
        return None
    limite = float(row[0])
    pct = (gasto_mes / limite) * 100
    if pct >= 100:
        return f"🚨 *LIMITE ATINGIDO — {categoria}!*\nVocê gastou R$ {gasto_mes:.2f} de R$ {limite:.2f} ({pct:.0f}%)."
    if pct >= 80:
        return f"⚠️ *Atenção — {categoria}:* {pct:.0f}% do orçamento usado.\nRestam R$ {limite - gasto_mes:.2f}."
    return None

def relatorio_orcamentos(numero):
    orcs = buscar_orcamentos(numero)
    if not orcs:
        return "📋 Nenhum orçamento definido ainda.\n\nExemplo:\n_orcamento Alimentacao 500_"
    linhas = ["📊 *Status dos seus orçamentos (este mês):*\n"]
    for o in orcs:
        cat = o["categoria"]
        limite = float(o["limite"])
        gasto = gasto_categoria_mes(numero, cat)
        pct = (gasto / limite) * 100
        barra = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        emoji = "✅" if pct < 80 else ("⚠️" if pct < 100 else "🚨")
        linhas.append(f"{emoji} *{cat}*\n{barra} {pct:.0f}%\nR$ {gasto:.2f} / R$ {limite:.2f}\n")
    return "\n".join(linhas)