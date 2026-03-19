import json
import streamlit as st
import pandas as pd
from chamada_ao_llm import (
    carregar_linhas_do_arquivo,
    preparar_itens_para_llm,
    extrair_json_da_resposta,
    normalizar_avaliacao,
    normalizar_saida,
    analisar_resenhas_com_llm,
    processar_resenhas,
    URL_ARQUIVO,
    BASE_URL_LLM,
    API_KEY_LLM,
    MODELO_LLM,
)

st.set_page_config(page_title="Análise de Resenhas", layout="wide")
st.title("🤖 Análise de Resenhas com IA")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")
    separador = st.text_input("Separador:", value=" | ")

# Abas
tab1, tab2, tab3 = st.tabs(["📥 Carregar", "📊 Análise", "📋 Resenhas"])

with tab1:
    if st.button("📡 Carregar Resenhas"):
        with st.spinner("Carregando..."):
            try:
                linhas = carregar_linhas_do_arquivo(URL_ARQUIVO)
                itens = preparar_itens_para_llm(linhas)
                st.session_state.itens = itens
                st.success(f"✅ {len(itens)} resenhas carregadas!")
            except Exception as e:
                st.error(f"❌ Erro: {e}")

with tab2:
    if "itens" in st.session_state:
        st.info("Clique abaixo para analisar com o modelo LM Studio...")
        if st.button("🔍 Analisar com LLM"):
            with st.spinner("Analisando..."):
                try:
                    resultado = analisar_resenhas_com_llm(st.session_state.itens)
                    st.session_state.resenhas = resultado
                    contagem, string_un = processar_resenhas(resultado, separador)
                    st.session_state.contagem = contagem
                    st.session_state.string_unificada = string_un
                    st.success("✅ Análise concluída!")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("😊 Positivas", contagem["positiva"])
                    with col2:
                        st.metric("😡 Negativas", contagem["negativa"])
                    with col3:
                        st.metric("😐 Neutras", contagem["neutra"])
                except Exception as e:
                    st.error(f"❌ Erro ao analisar: {e}")
    else:
        st.warning("👈 Carregue as resenhas primeiro!")

with tab3:
    if "resenhas" in st.session_state:
        st.dataframe(pd.DataFrame(st.session_state.resenhas), use_container_width=True)
        st.divider()
        st.subheader("String Unificada")
        st.text_area("Conteúdo:", value=st.session_state.string_unificada, height=200)
    else:
        st.warning("👈 Processe as resenhas primeiro!")