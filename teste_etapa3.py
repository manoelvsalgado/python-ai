"""Teste da etapa 3: processamento e análise de resenhas."""


def processar_resenhas(resenhas: list[dict[str, str]], separador: str = " | ") -> tuple[dict[str, int], str]:
    """
    Processa a lista de dicionários de resenhas.
    
    Retorna:
        Uma tupla com:
        - Dicionário com contagem de avaliações (positiva, negativa, neutra)
        - String contendo todos os itens unificados pelo separador
    """
    contagem = {"positiva": 0, "negativa": 0, "neutra": 0}
    itens_formatados = []
    
    for resenha in resenhas:
        # Conta as avaliações
        avaliacao = resenha.get("avaliacao", "").strip().lower()
        if avaliacao in contagem:
            contagem[avaliacao] += 1
        
        # Formata o item para a string unificada
        usuario = resenha.get("usuario", "")
        resenha_original = resenha.get("resenha_original", "")
        traducao_pt = resenha.get("traducao_pt", "")
        
        item_str = f"Usuário: {usuario} | Original: {resenha_original} | PT: {traducao_pt} | Avaliação: {avaliacao}"
        itens_formatados.append(item_str)
    
    string_unificada = separador.join(itens_formatados)
    
    return contagem, string_unificada


# Dados fictícios para teste
resenhas_teste = [
    {
        "usuario": "João Silva",
        "resenha_original": "App muito bom, recomendo!",
        "traducao_pt": "App muito bom, recomendo!",
        "avaliacao": "positiva"
    },
    {
        "usuario": "Maria Santos",
        "resenha_original": "Não funcionou direito",
        "traducao_pt": "Não funcionou direito",
        "avaliacao": "negativa"
    },
    {
        "usuario": "Pedro Costa",
        "resenha_original": "É ok, nada demais",
        "traducao_pt": "É ok, nada demais",
        "avaliacao": "neutra"
    },
    {
        "usuario": "Ana Oliveira",
        "resenha_original": "Excelente ferramenta!",
        "traducao_pt": "Excelente ferramenta!",
        "avaliacao": "positiva"
    },
    {
        "usuario": "Carlos Mendes",
        "resenha_original": "Decepcionante, esperava mais",
        "traducao_pt": "Decepcionante, esperava mais",
        "avaliacao": "negativa"
    }
]

if __name__ == "__main__":
    print("=== TESTE DA ETAPA 3 ===")
    print(f"Total de resenhas de teste: {len(resenhas_teste)}\n")
    
    # Chama a função de processamento
    contagem, string_unificada = processar_resenhas(resenhas_teste, separador=" || ")
    
    print("Contagem de Avaliações:")
    print(f"  ✓ Positivas: {contagem['positiva']}")
    print(f"  ✗ Negativas: {contagem['negativa']}")
    print(f"  ◯ Neutras: {contagem['neutra']}")
    
    print("\n" + "="*80)
    print("String Unificada das Resenhas:")
    print("="*80)
    print(string_unificada)
    print("\n" + "="*80)
    print(f"Tamanho total: {len(string_unificada)} caracteres")
