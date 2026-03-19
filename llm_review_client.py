import os
import json
from pathlib import Path
from langdetect import DetectorFactory, LangDetectException, detect_langs

try:
    from openai import OpenAI
except ModuleNotFoundError:
    OpenAI = None


DetectorFactory.seed = 0


SYSTEM_PROMPT = """Você é um especialista em análise de dados e conversão de dados para JSON.
Você receberá uma linha de texto que é uma resenha de um aplicativo em um marketplace online.
Eu quero que você analise essa resenha, e me retorne um JSON com as seguintes chaves:
- 'usuario': o nome do usuário que fez a resenha
- 'idioma': o idioma original predominante da resenha, em português (ex.: 'Inglês', 'Francês', 'Português')
- 'resenha_original': a resenha no idioma original que você recebeu
- 'resenha_pt': a resenha traduzida para o português, deve estar sempre na língua portuguesa
- 'avaliacao': uma avaliação se essa resenha foi 'Positiva', 'Negativa' ou 'Neutra' (apenas uma dessas opções)

Exemplo de entrada:
'879485937$Pedro Silva$This is a positive review for the app'
Exemplo de saída:
{
    "usuario": "Pedro Silva",
    "idioma": "Inglês",
    "resenha_original": "This is a positive review for the app",
    "resenha_pt": "Esta é uma resenha positiva para o aplicativo",
    "avaliacao": "Positiva"
}

Exemplo de entrada:
'74398793$John Myers$Je n'aime pas cette application'
Exemplo de saída:
{
    "usuario": "John Myers",
    "idioma": "Francês",
    "resenha_original": "Je n'aime pas cette application",
    "resenha_pt": "Eu não gosto dessa aplicação",
    "avaliacao": "Negativa"
}

Regra importante: você deve retornar apenas o JSON, sem nenhum outro texto além do JSON.
"""


def load_local_env_file(env_file: str = ".env"):
    env_path = Path(env_file)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_local_env_file()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("GEMMA_API_KEY") or "lm-studio"
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or os.getenv("GEMMA_BASE_URL")
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or os.getenv("GEMMA_MODEL") or "gpt-4o-mini"
DEMO_MODE = os.getenv("DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
DEMO_MODE_FALLBACK = os.getenv("DEMO_MODE_FALLBACK", "true").strip().lower() in {"1", "true", "yes", "on"}

client_openai = None


def can_use_online_llm():
    return (not DEMO_MODE) and OpenAI is not None and bool(OPENAI_BASE_URL)


def get_openai_client():
    global client_openai
    if client_openai is None and can_use_online_llm():
        client_openai = OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)
    return client_openai


def extract_review_fields(review_line):
    parts = review_line.split("$", 2)
    if len(parts) == 3:
        _, user_name, review_text = parts
        return user_name.strip() or "Usuario", review_text.strip()

    return "Usuario", review_line.strip()


LANGUAGE_LABELS = {
    "af": "Africâner",
    "ar": "Árabe",
    "bg": "Búlgaro",
    "bn": "Bengali",
    "ca": "Catalão",
    "cs": "Tcheco",
    "cy": "Galês",
    "da": "Dinamarquês",
    "de": "Alemão",
    "el": "Grego",
    "en": "Inglês",
    "es": "Espanhol",
    "et": "Estoniano",
    "fa": "Persa",
    "fi": "Finlandês",
    "fr": "Francês",
    "gu": "Gujarati",
    "he": "Hebraico",
    "hi": "Hindi",
    "hr": "Croata",
    "hu": "Húngaro",
    "id": "Indonésio",
    "it": "Italiano",
    "ja": "Japonês",
    "kn": "Canarês",
    "ko": "Coreano",
    "lt": "Lituano",
    "lv": "Letão",
    "mk": "Macedônio",
    "ml": "Malaiala",
    "mr": "Marathi",
    "ne": "Nepalês",
    "nl": "Holandês",
    "no": "Norueguês",
    "pa": "Punjabi",
    "pl": "Polonês",
    "pt": "Português",
    "ro": "Romeno",
    "ru": "Russo",
    "sk": "Eslovaco",
    "sl": "Esloveno",
    "so": "Somali",
    "sq": "Albanês",
    "sv": "Sueco",
    "sw": "Suaíli",
    "ta": "Tâmil",
    "te": "Telugu",
    "th": "Tailandês",
    "tl": "Tagalo",
    "tr": "Turco",
    "uk": "Ucraniano",
    "ur": "Urdu",
    "vi": "Vietnamita",
    "zh-cn": "Chinês",
    "zh-tw": "Chinês Tradicional",
    "zh": "Chinês",
}


PORTUGUESE_HINT_WORDS = {
    "muito", "bom", "boa", "otimo", "ótimo", "aplicativo", "nao", "não",
    "gostei", "amei", "recomendo", "funciona", "ruim", "excelente",
}


def portuguese_hint_score(review_text):
    lowered = review_text.lower()
    tokens = {token.strip(".,!?;:()[]{}\"'") for token in lowered.split()}
    token_hits = len(tokens.intersection(PORTUGUESE_HINT_WORDS))
    accent_hits = sum(1 for char in lowered if char in "ãõçáéíóúâêôà")
    return token_hits + accent_hits


def detect_review_language(review_text):
    if not review_text.strip():
        return "Idioma indefinido"

    # Textos muito curtos ou com poucos caracteres alfabéticos tendem a gerar falso positivo.
    alpha_count = sum(1 for char in review_text if char.isalpha())
    if alpha_count < 8:
        return "Idioma indefinido"

    hint_score = portuguese_hint_score(review_text)

    if alpha_count < 20 and hint_score >= 2:
        return "Português"

    try:
        candidates = detect_langs(review_text)
    except LangDetectException:
        return "Idioma indefinido"

    if not candidates:
        return "Idioma indefinido"

    top_candidate = candidates[0]
    top_code = top_candidate.lang.lower()
    top_prob = top_candidate.prob

    second_prob = candidates[1].prob if len(candidates) > 1 else 0.0
    confidence_gap = top_prob - second_prob

    # Se a confiança for baixa ou houver muita proximidade entre candidatos,
    # classificamos como idioma indefinido.
    if top_code == "pt" and top_prob >= 0.55 and hint_score >= 1:
        return "Português"

    if top_prob < 0.90 or confidence_gap < 0.20:
        return "Idioma indefinido"

    return LANGUAGE_LABELS.get(top_code, top_code)


def normalize_review_payload(review_line, payload):
    user_name, review_text = extract_review_fields(review_line)

    normalized_payload = {
        "usuario": payload.get("usuario") or user_name,
        "idioma": payload.get("idioma") or detect_review_language(review_text),
        "resenha_original": payload.get("resenha_original") or review_text,
        "resenha_pt": payload.get("resenha_pt") or review_text,
        "avaliacao": payload.get("avaliacao") or "Neutra",
    }
    return normalized_payload


def classify_sentiment_demo(review_text):
    text = review_text.lower()

    positive_words = [
        "good", "great", "excellent", "awesome", "love", "liked", "amazing", "best",
        "bom", "boa", "otimo", "ótimo", "excelente", "amei", "recomendo",
    ]
    negative_words = [
        "bad", "terrible", "awful", "hate", "worst", "bug", "broken", "slow", "crash",
        "ruim", "pessimo", "péssimo", "odiei", "horrivel", "horrível", "travando", "erro",
    ]

    positive_score = sum(1 for word in positive_words if word in text)
    negative_score = sum(1 for word in negative_words if word in text)

    if positive_score > negative_score:
        return "Positiva"
    if negative_score > positive_score:
        return "Negativa"
    return "Neutra"


def build_demo_json_response(review_line):
    user_name, review_text = extract_review_fields(review_line)
    payload = {
        "usuario": user_name,
        "idioma": detect_review_language(review_text),
        "resenha_original": review_text,
        "resenha_pt": review_text,
        "avaliacao": classify_sentiment_demo(review_text),
    }
    return json.dumps(payload, ensure_ascii=False)


def get_runtime_mode_label():
    if DEMO_MODE:
        return "DEMO_MODE (analise local)"

    if not can_use_online_llm():
        return "DEMO_MODE fallback (configuracao online ausente)"

    return f"LLM online ({OPENAI_MODEL})"

def parse_review_line_to_json(review_line):
    if DEMO_MODE:
        demo_response = build_demo_json_response(review_line)
        print(demo_response)
        return demo_response

    if not can_use_online_llm():
        print("[WARN] Configuracao online ausente/invalida. Usando DEMO_MODE fallback.")
        demo_response = build_demo_json_response(review_line)
        print(demo_response)
        return demo_response

    try:
        llm_response = get_openai_client().chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role":"system",
                "content": SYSTEM_PROMPT},

                {"role":"user",
                "content": f"Resenha: {review_line}"}
            ],
            temperature=0.0
        )

        response_content = llm_response.choices[0].message.content or ""
        cleaned_response = response_content.replace("```json", "").replace("```", "").strip()
        parsed_payload = json.loads(cleaned_response)
        normalized_payload = normalize_review_payload(review_line, parsed_payload)
        normalized_response = json.dumps(normalized_payload, ensure_ascii=False)
        print(normalized_response)
        return normalized_response
    except Exception as exc:
        if not DEMO_MODE_FALLBACK:
            raise

        print(f"[WARN] Falha no LLM online ({exc}). Usando DEMO_MODE fallback.")
        demo_response = build_demo_json_response(review_line)
        print(demo_response)
        return demo_response