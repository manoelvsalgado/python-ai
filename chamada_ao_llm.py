import json
import os
from urllib.request import Request, urlopen

import pandas as pd
from openai import OpenAI


URL_ARQUIVO = "https://cdn3.gnarususercontent.com.br/4790-python/Resenhas_App_ChatGPT.txt"
BASE_URL_LLM = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:1234/v1")
API_KEY_LLM = os.getenv("LOCAL_LLM_API_KEY", "lm-studio")
MODELO_LLM = os.getenv("LOCAL_LLM_MODEL", "google/gemma-3-4b")


def carregar_linhas_do_arquivo(url: str) -> list[str]:
    """Baixa um arquivo .txt de uma URL e retorna suas linhas em uma lista."""
    requisicao = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(requisicao) as resposta:
        conteudo = resposta.read().decode("utf-8")

    # O pandas facilita manipulação posterior das linhas antes de enviar ao LLM.
    df_resenhas = pd.DataFrame({"linha": conteudo.splitlines()})
    return df_resenhas["linha"].tolist()


def preparar_itens_para_llm(linhas: list[str]) -> list[dict[str, str]]:
    """Extrai usuario e resenha original de cada linha no formato id$usuario$resenha."""
    df = pd.DataFrame({"linha": linhas})
    partes = df["linha"].str.split("$", n=2, expand=True)

    df["usuario"] = partes[1].fillna("").str.strip()
    df["resenha_original"] = partes[2].fillna("").str.strip()
    df = df[(df["usuario"] != "") & (df["resenha_original"] != "")]

    return df[["usuario", "resenha_original"]].to_dict(orient="records")


def extrair_json_da_resposta(texto: str) -> list[dict]:
    """Extrai JSON da resposta textual do modelo, inclusive quando vem com bloco markdown."""
    conteudo = texto.strip()

    if conteudo.startswith("```"):
        linhas = [linha for linha in conteudo.splitlines() if not linha.strip().startswith("```")]
        conteudo = "\n".join(linhas).strip()

    dados = json.loads(conteudo)

    if isinstance(dados, list):
        return dados

    if isinstance(dados, dict):
        for chave in ("resenhas", "itens", "dados", "reviews"):
            valor = dados.get(chave)
            if isinstance(valor, list):
                return valor

    raise ValueError("O modelo não retornou uma lista JSON válida.")


def normalizar_avaliacao(valor: str) -> str:
    texto = (valor or "").strip().lower()
    if texto in {"positivo", "positiva", "positive"}:
        return "positiva"
    if texto in {"negativo", "negativa", "negative"}:
        return "negativa"
    if texto in {"neutro", "neutra", "neutral"}:
        return "neutra"
    return "neutra"


def normalizar_saida(
    itens_base: list[dict[str, str]],
    saida_modelo: list[dict],
) -> list[dict[str, str]]:
    """Garante a estrutura final pedida no desafio."""
    resultado = []

    for i, base in enumerate(itens_base):
        item = saida_modelo[i] if i < len(saida_modelo) and isinstance(saida_modelo[i], dict) else {}

        resultado.append(
            {
                "usuario": item.get("usuario") or item.get("user") or base["usuario"],
                "resenha_original": item.get("resenha_original") or base["resenha_original"],
                "traducao_pt": item.get("traducao_pt") or item.get("traducao") or "",
                "avaliacao": normalizar_avaliacao(item.get("avaliacao") or item.get("sentimento") or ""),
            }
        )

    return resultado


def analisar_resenhas_com_llm(itens: list[dict[str, str]]) -> list[dict[str, str]]:
    """Envia os itens para o modelo local e retorna uma lista de dicionarios em JSON."""
    cliente = OpenAI(base_url=BASE_URL_LLM, api_key=API_KEY_LLM)

    mensagem_sistema = (
        "Voce eh um classificador de resenhas. "
        "Responda SOMENTE com JSON valido, sem texto extra."
    )

    mensagem_usuario = (
        "Receba a lista abaixo e devolva uma lista JSON na mesma ordem, com os campos: "
        "usuario, resenha_original, traducao_pt, avaliacao. "
        "A avaliacao deve ser apenas positiva, negativa ou neutra.\n\n"
        f"Entrada:\n{json.dumps(itens, ensure_ascii=False)}"
    )

    resposta = cliente.chat.completions.create(
        model=MODELO_LLM,
        messages=[
            {"role": "system", "content": mensagem_sistema},
            {"role": "user", "content": mensagem_usuario},
        ],
        temperature=0.2,
    )

    conteudo = resposta.choices[0].message.content or ""
    saida_modelo = extrair_json_da_resposta(conteudo)

    return normalizar_saida(itens, saida_modelo)


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


if __name__ == "__main__":
    linhas = carregar_linhas_do_arquivo(URL_ARQUIVO)
    itens = preparar_itens_para_llm(linhas)

    print(f"Total de linhas carregadas: {len(linhas)}")
    print(f"Total de itens preparados para o LLM: {len(itens)}")

    try:
        resultado_json = analisar_resenhas_com_llm(itens)
    except Exception as erro:
        print("Erro ao consultar o modelo local.")
        print(
            "Confirme se LM Studio ou Ollama estao rodando e ajuste as variaveis "
            "LOCAL_LLM_BASE_URL e LOCAL_LLM_MODEL se necessario."
        )
        print(f"Detalhe: {erro}")
    else:
        print("\n=== ETAPA 2: Respostas do Modelo em JSON ===")
        print(json.dumps(resultado_json, ensure_ascii=False, indent=2))
        
        print("\n=== ETAPA 3: Processamento e Análise ===")
        contagem, string_unificada = processar_resenhas(resultado_json, separador=" | ")
        
        print("\nContagem de Avaliações:")
        print(f"  Positivas: {contagem['positiva']}")
        print(f"  Negativas: {contagem['negativa']}")
        print(f"  Neutras: {contagem['neutra']}")
        
        print("\nString Unificada (primeiros 500 caracteres):")
        print(f"  {string_unificada[:500]}...")
        print(f"\nTamanho total da string: {len(string_unificada)} caracteres")