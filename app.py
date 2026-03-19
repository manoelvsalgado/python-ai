import json
import io
from collections import Counter

import streamlit as st
from review_analysis_pipeline import build_reviews_json, count_and_join_reviews
from llm_review_client import get_runtime_mode_label

# ── Página ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Análise de Resenhas",
    page_icon="💬",
    layout="centered",
)

st.title("💬 Análise de Resenhas de Aplicativos")
st.caption(f"Modo de análise: **{get_runtime_mode_label()}**")
st.markdown(
    "Faça upload de um arquivo `.txt` com as resenhas no formato  \n"
    "`ID$Nome do Usuário$Texto da resenha`  \n"
    "ou use o arquivo de exemplo abaixo."
)

# ── Upload ou arquivo de exemplo ──────────────────────────────────────────────
uploaded_file = st.file_uploader("Escolha o arquivo de resenhas (.txt)", type="txt")

use_sample = st.checkbox("Usar arquivo de exemplo (app_reviews.txt)", value=not bool(uploaded_file))

if uploaded_file:
    raw_text = uploaded_file.read().decode("utf-8", errors="replace")
elif use_sample:
    try:
        with open("app_reviews.txt", "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()
    except FileNotFoundError:
        st.error("Arquivo app_reviews.txt não encontrado. Faça upload de um arquivo.")
        st.stop()
else:
    st.info("Selecione um arquivo ou marque 'Usar arquivo de exemplo' para começar.")
    st.stop()

review_lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
st.write(f"**{len(review_lines)} resenhas** encontradas no arquivo.")

# ── Processar ─────────────────────────────────────────────────────────────────
if st.button("🔍 Analisar Resenhas", type="primary"):
    progress = st.progress(0, text="Processando resenhas...")
    reviews_json = []

    for i, line in enumerate(review_lines):
        result = build_reviews_json([line])
        reviews_json.extend(result)
        progress.progress((i + 1) / len(review_lines), text=f"Processando {i + 1}/{len(review_lines)}...")

    progress.empty()
    st.session_state["reviews_json"] = reviews_json

# ── Exibir resultados (persiste mesmo após rerun do dropdown) ──────────────────
if "reviews_json" in st.session_state:
    reviews_json = st.session_state["reviews_json"]
    positives, negatives, neutrals, _ = count_and_join_reviews(reviews_json)
    language_counts = Counter(review.get("idioma", "Não identificado") for review in reviews_json)

    # ── Métricas ──────────────────────────────────────────────────────────────
    st.subheader("📊 Resumo")
    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Positivas", positives)
    col2.metric("❌ Negativas", negatives)
    col3.metric("➖ Neutras", neutrals)

    # ── Gráfico de pizza ──────────────────────────────────────────────────────
    try:
        import matplotlib.pyplot as plt

        sentiment_col, language_col = st.columns(2)

        with sentiment_col:
            labels = []
            sizes = []
            colors = []
            color_map = {"Positivas": "#4CAF50", "Negativas": "#F44336", "Neutras": "#9E9E9E"}

            for label, count in [("Positivas", positives), ("Negativas", negatives), ("Neutras", neutrals)]:
                if count > 0:
                    labels.append(f"{label} ({count})")
                    sizes.append(count)
                    colors.append(color_map[label])

            if sizes:
                fig, ax = plt.subplots(figsize=(4, 4))
                ax.pie(sizes, labels=labels, colors=colors, autopct="%1.0f%%", startangle=90)
                ax.set_title("Distribuição de Sentimentos")
                st.pyplot(fig)

        with language_col:
            language_labels = []
            language_sizes = []

            for language, count in sorted(language_counts.items(), key=lambda item: (-item[1], item[0])):
                language_labels.append(f"{language} ({count})")
                language_sizes.append(count)

            if language_sizes:
                fig, ax = plt.subplots(figsize=(4, 4))
                ax.pie(language_sizes, labels=language_labels, autopct="%1.0f%%", startangle=90)
                ax.set_title("Distribuição por Idioma")
                st.pyplot(fig)
    except ModuleNotFoundError:
        pass  # matplotlib opcional

    # ── Tabela de resultados ──────────────────────────────────────────────────
    st.subheader("📋 Resenhas Analisadas")

    filter_col_1, filter_col_2 = st.columns(2)
    with filter_col_1:
        sentiment_filter = st.selectbox(
            "Filtrar por sentimento",
            ["Todas", "Positiva", "Negativa", "Neutra"],
        )
    with filter_col_2:
        language_filter = st.selectbox(
            "Filtrar por idioma",
            ["Todos"] + sorted(language_counts.keys()),
        )

    filtered = reviews_json
    if sentiment_filter != "Todas":
        filtered = [r for r in reviews_json if r.get("avaliacao") == sentiment_filter]
    if language_filter != "Todos":
        filtered = [r for r in filtered if r.get("idioma", "Não identificado") == language_filter]

    for review in filtered:
        sentiment = review.get("avaliacao", "Neutra")
        icon = {"Positiva": "✅", "Negativa": "❌", "Neutra": "➖"}.get(sentiment, "➖")

        with st.expander(f"{icon} {review.get('usuario', 'Usuário')} — {sentiment} — {review.get('idioma', 'Não identificado')}"):
            st.markdown(f"**Idioma:** {review.get('idioma', 'Não identificado')}")
            st.markdown(f"**Original:** {review.get('resenha_original', '')}")
            st.markdown(f"**Tradução (PT):** {review.get('resenha_pt', '')}")

    # ── Download JSON ─────────────────────────────────────────────────────────
    st.subheader("⬇️ Exportar")
    json_bytes = io.BytesIO(json.dumps(reviews_json, ensure_ascii=False, indent=2).encode("utf-8"))
    st.download_button(
        label="Baixar resultados em JSON",
        data=json_bytes,
        file_name="resultados_resenhas.json",
        mime="application/json",
    )
