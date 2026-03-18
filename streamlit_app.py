# -*- coding: utf-8 -*-
"""
streamlit_app.py
----------------
Interfaz web con Streamlit para el generador de artículos técnicos con IA.

Ejecutar con:
    streamlit run streamlit_app.py
"""

import json
import os
import tempfile

import streamlit as st

from seed_data import TAXONOMY
from generateArticle import (
    ARTICLE_LANGUAGE,
    AUTHOR_USERNAME,
    GEMINI_API_KEY,
    OLLAMA_BASE_URL,
    OLLAMA_PLACEHOLDER_API_KEY,
    OPENAIAPIKEY,
    OPENAI_MODEL,
    SITE,
    _is_gemini_model,
    _is_ollama_provider,
    generate_and_save_article,
)

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment,misc]

# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _build_category_map():
    """Return nested dicts mapping categories → subcategories → tags from TAXONOMY."""
    cat_map: dict = {}
    for cat in TAXONOMY:
        sub_map: dict = {}
        for sub in cat.get("subcategories", []):
            sub_map[sub["name"]] = sub.get("tags", [])
        cat_map[cat["name"]] = sub_map
    return cat_map


def _init_client():
    """Initialise the AI client based on environment configuration."""
    using_gemini = _is_gemini_model(OPENAI_MODEL)
    using_ollama = _is_ollama_provider()

    if using_ollama:
        return OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_PLACEHOLDER_API_KEY)
    if not using_gemini:
        if not OPENAIAPIKEY:
            return None
        return OpenAI(api_key=OPENAIAPIKEY)
    # Gemini uses LangChain internally, no SDK client needed
    return None


# ──────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Generador de Artículos con IA",
    page_icon="📝",
    layout="wide",
)

st.title("📝 Generador de Artículos con IA")
st.markdown(
    "Genera artículos técnicos optimizados para SEO con **OpenAI**, "
    "**Google Gemini** u **Ollama**."
)

# ──────────────────────────────────────────────────────────────────
# Sidebar – inputs
# ──────────────────────────────────────────────────────────────────

cat_map = _build_category_map()
category_names = list(cat_map.keys())

with st.sidebar:
    st.header("⚙️ Parámetros del artículo")

    category = st.selectbox("Categoría", options=category_names, index=0)

    subcategory_names = list(cat_map.get(category, {}).keys())
    subcategory = st.selectbox(
        "Subcategoría",
        options=subcategory_names if subcategory_names else ["General"],
        index=0,
    )

    tag_options = cat_map.get(category, {}).get(subcategory, [])
    tag = st.selectbox(
        "Tag / Tema",
        options=["(ninguno)"] + tag_options,
        index=0,
    )
    if tag == "(ninguno)":
        tag = None

    st.divider()
    st.subheader("Opciones avanzadas")

    language = st.text_input("Idioma (ISO 639-1)", value=ARTICLE_LANGUAGE)
    author = st.text_input("Autor", value=AUTHOR_USERNAME)
    site = st.text_input("URL del sitio", value=SITE)
    custom_title = st.text_input("Título personalizado (opcional)")
    avoid_titles_raw = st.text_area(
        "Títulos a evitar (uno por línea)",
        help="Si el título generado es demasiado similar a alguno de estos, se regenerará.",
    )

    if _is_ollama_provider():
        provider_label = "Ollama"
    elif _is_gemini_model(OPENAI_MODEL):
        provider_label = "Gemini"
    else:
        provider_label = "OpenAI"
    st.info(f"**Proveedor IA:** {provider_label}  \n**Modelo:** `{OPENAI_MODEL}`")

# ──────────────────────────────────────────────────────────────────
# Main area – generate button + results
# ──────────────────────────────────────────────────────────────────

generate_btn = st.button("🚀 Generar artículo", type="primary", use_container_width=True)

if generate_btn:
    avoid_titles = [t.strip() for t in avoid_titles_raw.splitlines() if t.strip()] if avoid_titles_raw else []

    with st.spinner("Generando artículo con IA — esto puede tardar unos segundos…"):
        try:
            client_ai = _init_client()

            with tempfile.NamedTemporaryFile(
                suffix=".json", delete=False, mode="w", encoding="utf-8"
            ) as tmp:
                tmp_path = tmp.name

            success = generate_and_save_article(
                client_ai=client_ai,
                tag_text=tag,
                parent_name=category,
                subcat_name=subcategory,
                avoid_titles=avoid_titles if avoid_titles else None,
                author_name=author,
                site=site,
                language=language,
                output_path=tmp_path,
                title=custom_title if custom_title else None,
            )

            if success:
                with open(tmp_path, encoding="utf-8") as f:
                    article = json.load(f)

                st.success(f"✅ Artículo generado: **{article.get('title', '')}**")

                tab_preview, tab_meta, tab_json = st.tabs(
                    ["📄 Vista previa", "🔍 Metadatos SEO", "📋 JSON completo"]
                )

                with tab_preview:
                    st.subheader(article.get("title", ""))
                    st.caption(
                        f"🏷️ {article.get('category', '')} · "
                        f"⏱️ {article.get('readingTime', 0)} min · "
                        f"📏 {article.get('wordCount', 0)} palabras"
                    )
                    st.markdown(article.get("summary", ""), unsafe_allow_html=False)
                    st.divider()
                    st.markdown(article.get("body", ""), unsafe_allow_html=True)

                with tab_meta:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Palabras", article.get("wordCount", 0))
                        st.metric("Lectura (min)", article.get("readingTime", 0))
                    with col2:
                        st.metric("Meta título", f"{len(article.get('metaTitle', ''))} chars")
                        st.metric("Meta descripción", f"{len(article.get('metaDescription', ''))} chars")

                    st.text_input("Meta Title", value=article.get("metaTitle", ""), disabled=True)
                    st.text_area("Meta Description", value=article.get("metaDescription", ""), disabled=True)
                    st.text_input("Canonical URL", value=article.get("canonicalUrl", ""), disabled=True)
                    st.text_input("OG Title", value=article.get("ogTitle", ""), disabled=True)
                    st.text_area("Keywords", value=", ".join(article.get("keywords", [])), disabled=True)
                    if article.get("structuredData"):
                        st.json(article["structuredData"])

                with tab_json:
                    json_str = json.dumps(article, ensure_ascii=False, indent=2)
                    st.code(json_str, language="json")

                # Download button
                json_bytes = json.dumps(article, ensure_ascii=False, indent=2).encode("utf-8")
                st.download_button(
                    "⬇️ Descargar JSON",
                    data=json_bytes,
                    file_name=f"{article.get('slug', 'article')}.json",
                    mime="application/json",
                    use_container_width=True,
                )
            else:
                st.error("❌ No se pudo generar el artículo. Revisa los logs para más detalles.")

            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        except Exception as exc:
            st.error(f"❌ Error durante la generación: {exc}")
