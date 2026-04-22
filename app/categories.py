CATEGORIAS = {
    "Alimentacao": ["mercado","supermercado","padaria","restaurante","almoco","jantar","cafe","pizza","hamburguer","ifood","comida","lanche","pao","carne","frango","peixe","acai","salgado"],
    "Transporte": ["uber","99","taxi","onibus","metro","combustivel","gasolina","etanol","diesel","pedagio","estacionamento","passagem","bilhete","trem"],
    "Saude": ["farmacia","remedio","medicamento","medico","consulta","exame","hospital","dentista","academia","suplemento","vitamina"],
    "Lazer": ["cinema","teatro","show","festa","bar","cerveja","netflix","spotify","amazon","disney","viagem","hotel","passeio","parque","ingresso"],
    "Casa": ["aluguel","condominio","luz","energia","agua","gas","internet","telefone","limpeza","faxina","moveis","manutencao"],
    "Educacao": ["escola","faculdade","curso","livro","apostila","mensalidade","seminario","conferencia","treinamento"],
    "Vestuario": ["roupa","sapato","tenis","camisa","calca","vestido","bermuda","meia","bolsa","mochila"],
}

def detectar_categoria(texto):
    t = texto.lower()
    for cat, palavras in CATEGORIAS.items():
        for p in palavras:
            if p in t:
                return cat
    return "Outros"

def listar_categorias():
    return list(CATEGORIAS.keys()) + ["Outros"]