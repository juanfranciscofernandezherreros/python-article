"""
Módulo principal de generación de artículos con IA.

Este fichero actúa como punto de entrada CLI y como fachada pública que
re-exporta todos los símbolos de los submódulos para mantener la
compatibilidad con el código y los tests existentes.

Submódulos:
  config           – Constantes y configuración del entorno.
  utils            – Funciones auxiliares genéricas.
  html_utils       – Utilidades de procesamiento HTML.
  seo              – Funciones SEO (canonical URL, JSON-LD).
  notifications    – Sistema de notificaciones y email.
  prompts          – Construcción de prompts para la IA.
  ai_providers     – Proveedores de IA (LangChain, Ollama, Gemini).
  article_generator – Generación y guardado de artículos.
"""
from __future__ import annotations

import argparse
import json
import smtplib  # noqa: F401 – re-exportado para compatibilidad con tests
import sys

from openai import OpenAI

# ── Re-exportar todos los símbolos públicos de los submódulos ──────────
from config import (  # noqa: F401
    AI_PROVIDER,
    ARTICLE_LANGUAGE,
    AI_TEMPERATURE_ARTICLE,
    AI_TEMPERATURE_TITLE,
    AUTHOR_USERNAME,
    FROM_EMAIL,
    GEMINI_API_KEY,
    GENERATION_SYSTEM_MSG,
    MAX_AVOID_TITLES_IN_PROMPT,
    MAX_TITLE_RETRIES,
    META_DESCRIPTION_MAX_LENGTH,
    META_TITLE_MAX_LENGTH,
    NOTIFY_VERBOSE,
    OLLAMA_BASE_URL,
    OLLAMA_PLACEHOLDER_API_KEY,
    OPENAIAPIKEY,
    OPENAI_MAX_ARTICLE_TOKENS,
    OPENAI_MAX_RETRIES,
    OPENAI_MAX_TITLE_TOKENS,
    OPENAI_MODEL,
    OPENAI_RETRY_BASE_DELAY,
    OUTPUT_FILENAME,
    OUTPUT_FILENAME_PATTERN,
    SEND_EMAILS,
    SEND_PROMPT_EMAIL,
    SIMILARITY_THRESHOLD_DEFAULT,
    SIMILARITY_THRESHOLD_STRICT,
    SITE,
    SMTP_HOST,
    SMTP_PASS,
    SMTP_PORT,
    SMTP_USER,
    TITLE_SYSTEM_MSG,
    TO_EMAIL,
    _LANGUAGE_NAMES,
    _language_name,
    logger,
)
from utils import (  # noqa: F401
    as_list,
    html_escape,
    is_too_similar,
    normalize_for_similarity,
    now_utc,
    similar_ratio,
    slugify,
    str_id,
    tag_name,
)
from html_utils import (  # noqa: F401
    _replace_h1,
    count_words,
    estimate_reading_time,
    extract_plain_text,
)
from seo import (  # noqa: F401
    build_canonical_url,
    build_json_ld_structured_data,
)
from notifications import (  # noqa: F401
    notify,
    send_notification_email,
)
from prompts import (  # noqa: F401
    build_generation_prompt,
    build_title_prompt,
    email_generation_prompt,
)
from ai_providers import (  # noqa: F401
    ChatGoogleGenerativeAI,
    ChatOpenAI,
    ChatPromptTemplate,
    LLMChain,
    StrOutputParser,
    _extract_json_block,
    _generate_with_langchain,
    _is_gemini_model,
    _is_ollama_provider,
    _retry_with_backoff,
    _safe_json_loads,
)
from article_generator import (  # noqa: F401
    generate_and_save_article,
    generate_article_with_ai,
    generate_title_with_ai,
)


# ============ HELPERS ============

def _build_client_ai() -> "OpenAI | None":
    """Validate API keys and initialise the AI client (OpenAI / Ollama / Gemini)."""
    using_gemini = _is_gemini_model(OPENAI_MODEL)
    using_ollama = _is_ollama_provider()

    if using_ollama:
        try:
            client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_PLACEHOLDER_API_KEY)
            notify("Ollama listo", f"Modelo: {OPENAI_MODEL} — URL: {OLLAMA_BASE_URL}", level="info", always_email=True)
            return client
        except Exception as e:
            notify("Error inicializando Ollama", str(e), level="error", always_email=True)
            sys.exit(1)
    elif using_gemini:
        if not GEMINI_API_KEY:
            notify("Configuración incompleta", "Falta la variable de entorno GEMINI_API_KEY.", level="error", always_email=True)
            sys.exit(1)
        notify("Gemini listo", f"Modelo: {OPENAI_MODEL}", level="info", always_email=True)
        return None
    else:
        if not OPENAIAPIKEY:
            notify("Configuración incompleta", "Falta la variable de entorno OPENAIAPIKEY.", level="error", always_email=True)
            sys.exit(1)
        try:
            client = OpenAI(api_key=OPENAIAPIKEY)
            notify("OpenAI listo", f"Modelo: {OPENAI_MODEL}", level="info", always_email=True)
            return client
        except Exception as e:
            notify("Error inicializando OpenAI", str(e), level="error", always_email=True)
            sys.exit(1)


def _parse_avoid_titles(raw: str) -> list[str]:
    """Split a semicolon-separated string into a list of non-empty title strings."""
    return [t.strip() for t in raw.split(";") if t.strip()] if raw else []


def _run_single(client_ai: "OpenAI | None", args: argparse.Namespace) -> None:
    """Execute a single article generation job from parsed CLI args."""
    avoid_titles = _parse_avoid_titles(args.avoid_titles)

    notify("Inicio de proceso", "Comenzando generación de artículo.", level="info", always_email=True)

    try:
        created = generate_and_save_article(
            client_ai=client_ai,
            tag_text=args.tag,
            parent_name=args.category,
            subcat_name=args.subcategory,
            avoid_titles=avoid_titles,
            author_name=args.username,
            site=args.site,
            language=args.language,
            output_path=args.output,
            title=args.title,
        )
    except Exception as e:
        notify("Error generando artículo", str(e), level="error", always_email=True)
        sys.exit(1)

    if created:
        notify("Proceso terminado", f"Artículo guardado en '{args.output}'.", level="success", always_email=True)
        print(f"\n🟩 Proceso terminado. Artículo guardado en '{args.output}'.")
    else:
        notify("Proceso terminado", "No se pudo generar el artículo.", level="warning", always_email=True)
        print("\n🟩 Proceso terminado. No se pudo generar el artículo.")


def _run_batch(client_ai: "OpenAI | None", args: argparse.Namespace) -> None:
    """Load a batch JSON file and run jobs sequentially.

    Each entry in the JSON array can contain the same fields as the CLI
    arguments (``tag``, ``category``, ``subcategory``, ``output``,
    ``username``, ``site``, ``language``, ``title``, ``avoid_titles``,
    ``provider``).  CLI arguments act as default values for any field
    omitted in a batch entry.  If ``output`` is omitted in a batch entry,
    the filename defaults to ``article_{index}.json`` (1-based index).
    """
    try:
        with open(args.batch, encoding="utf-8") as fh:
            jobs = json.load(fh)
    except FileNotFoundError:
        notify("Error de lote", f"Fichero de lote no encontrado: '{args.batch}'", level="error", always_email=True)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        notify("Error de lote", f"JSON inválido en fichero de lote: {exc}", level="error", always_email=True)
        sys.exit(1)

    if not isinstance(jobs, list):
        notify("Error de lote", "El fichero de lote debe ser un array JSON de trabajos.", level="error", always_email=True)
        sys.exit(1)

    if not jobs:
        notify("Lote vacío", "El fichero de lote no contiene trabajos.", level="warning", always_email=True)
        print("\n⚠️  El fichero de lote está vacío.")
        return

    notify("Inicio de lote", f"Procesando {len(jobs)} trabajo(s) secuencialmente.", level="info", always_email=True)
    print(f"\n🔄 Iniciando lote: {len(jobs)} trabajo(s).")

    success_count = 0
    fail_count = 0

    # Save the global provider so per-job overrides don't leak into subsequent jobs
    import config as _cfg
    _original_provider = _cfg.AI_PROVIDER

    for idx, job in enumerate(jobs, start=1):
        if not isinstance(job, dict):
            notify(f"Trabajo {idx} inválido", f"El trabajo {idx} no es un objeto JSON válido.", level="error", always_email=True)
            print(f"  [{idx}/{len(jobs)}] ❌ El trabajo no es un objeto JSON válido.")
            fail_count += 1
            continue

        # category is required per job (CLI --category acts as fallback)
        category = job.get("category") or args.category
        if not category:
            notify(f"Trabajo {idx} inválido", f"El trabajo {idx} no tiene 'category'.", level="error", always_email=True)
            print(f"  [{idx}/{len(jobs)}] ❌ Falta el campo 'category'.")
            fail_count += 1
            continue

        tag = job.get("tag", args.tag)
        subcategory = job.get("subcategory", args.subcategory)
        output_raw = job.get("output")
        output_path = output_raw if output_raw is not None else f"article_{idx}.json"
        username = job.get("username", args.username)
        site = job.get("site", args.site)
        language = job.get("language", args.language)
        title = job.get("title", args.title)
        avoid_titles = _parse_avoid_titles(job.get("avoid_titles", args.avoid_titles))

        # Per-job provider override — restore after each job so overrides don't leak
        job_provider = job.get("provider")
        _cfg.AI_PROVIDER = job_provider if job_provider is not None else _original_provider

        print(f"\n  [{idx}/{len(jobs)}] tag='{tag}' | category='{category}' | output='{output_path}'")
        notify(
            f"Trabajo {idx}/{len(jobs)}",
            f"tag='{tag}', category='{category}', output='{output_path}'",
            level="info",
            always_email=True,
        )

        try:
            created = generate_and_save_article(
                client_ai=client_ai,
                tag_text=tag,
                parent_name=category,
                subcat_name=subcategory,
                avoid_titles=avoid_titles,
                author_name=username,
                site=site,
                language=language,
                output_path=output_path,
                title=title,
            )
            if created:
                success_count += 1
                print(f"       ✅ Artículo guardado en '{output_path}'.")
            else:
                fail_count += 1
                print("       ⚠️  No se pudo generar el artículo.")
        except Exception as exc:
            fail_count += 1
            notify(f"Error en trabajo {idx}", str(exc), level="error", always_email=True)
            print(f"       ❌ Error: {exc}")

    summary_level = "success" if fail_count == 0 else "warning"
    notify(
        "Lote completado",
        f"{success_count} éxito(s), {fail_count} error(es).",
        level=summary_level,
        always_email=True,
    )
    print(f"\n🟩 Lote completado: {success_count} éxito(s), {fail_count} error(es).")


# ============ MAIN ============
def main():
    parser = argparse.ArgumentParser(
        description="Genera un artículo técnico con IA y lo exporta a un fichero JSON.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--batch", "-b", default=None,
                        help="Ruta a un fichero JSON con una lista de trabajos a ejecutar "
                             "secuencialmente. Cada entrada acepta los mismos campos que los "
                             "argumentos CLI (tag, category, subcategory, output, username, "
                             "site, language, title, avoid_titles, provider). Los argumentos "
                             "CLI actúan como valores por defecto para los campos omitidos.")
    parser.add_argument("--tag", "-t", default=None,
                        help="Tema o tag del artículo (opcional)")
    parser.add_argument("--category", "-c", default=None,
                        help="Nombre de la categoría padre (requerido, salvo en modo --batch "
                             "donde puede indicarse por trabajo)")
    parser.add_argument("--subcategory", "-s", default="General",
                        help="Nombre de la subcategoría")
    parser.add_argument("--output", "-o", default=OUTPUT_FILENAME,
                        help="Ruta del fichero JSON de salida (también configurable con OUTPUT_FILENAME en .env)")
    parser.add_argument("--username", "--author", "-u", "-a",
                        dest="username",
                        default=AUTHOR_USERNAME,
                        help="Username/nombre del autor (también configurable con AUTHOR_USERNAME en .env)")
    parser.add_argument("--site", "-S",
                        default=SITE,
                        help="URL base del sitio para URLs canónicas (p. ej. https://myblog.com), también configurable con SITE en .env")
    parser.add_argument("--language", "-l", default=ARTICLE_LANGUAGE,
                        help="Código de idioma ISO 639-1 (p. ej. es, en, fr)")
    parser.add_argument("--title", "-T", default=None,
                        help="Título del artículo (si se omite, se genera con IA)")
    parser.add_argument("--provider", "-p",
                        choices=["auto", "openai", "gemini", "ollama"],
                        default=None,
                        help="Proveedor de IA a usar (auto detecta por modelo/URL). "
                             "También configurable con AI_PROVIDER en .env")
    parser.add_argument("--avoid-titles", default="",
                        help="Títulos a evitar, separados por ';'")
    args = parser.parse_args()

    # Validate: either --batch or --category must be provided
    if args.batch is None and args.category is None:
        parser.error("Se requiere --category (o usar --batch para proporcionar múltiples trabajos)")

    # Aplicar el proveedor de IA seleccionado por CLI (sobreescribe AI_PROVIDER del .env)
    if args.provider is not None:
        import config as _cfg
        _cfg.AI_PROVIDER = args.provider

    client_ai = _build_client_ai()

    if args.batch is not None:
        _run_batch(client_ai, args)
    else:
        _run_single(client_ai, args)

if __name__ == "__main__":
    main()
