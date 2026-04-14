import requests
import json
import os
from app.debug_tools import debug_wrap

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama-agent:11434")
MODEL_NAME = "llama3.2:1b"


@debug_wrap
def generate_copil_text(context: dict, return_raw: bool = False):

    # --- PROMPT ---
    prompt = f"""
Tu es un agent qui prépare une slide de COPIL budget.

Voici les données de contexte (JSON) :
{json.dumps(context, ensure_ascii=False, indent=2)}

Génère STRICTEMENT un JSON avec la structure suivante :

{{
  "title": "...",
  "subtitle": "...",
  "key_message": "...",
  "justifications": ["...", "...", "..."]
}}

Contraintes :
- Réponds UNIQUEMENT avec ce JSON.
- Pas de texte avant ou après.
- 3 justifications maximum.
"""

    # --- APPEL OLLAMA /api/chat ---
    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "Tu génères STRICTEMENT un JSON valide, sans texte autour."},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        },
        timeout=600,
    )

    # --- DEBUG ---
    print("🔍 Modèle demandé :", MODEL_NAME)
    print("🔍 Réponse brute Ollama :", response.text[:500])

    response.raise_for_status()

    # --- EXTRACTION DU TEXTE RENVOYÉ PAR LE LLM ---
    try:
        raw_text = response.json()["message"]["content"]
    except Exception as e:
        raise ValueError(f"Réponse Ollama invalide : {e}\nContenu brut : {response.text}")

    # --- DEBUG RAW ---
    with open("/data-agent/debug_llm_raw.txt", "w", encoding="utf-8") as f:
        f.write(raw_text)

    if return_raw:
        return raw_text

    # --- PARSING DIRECT DU JSON ---
    try:
        final_json = json.loads(raw_text)
    except Exception as e:
        raise ValueError(f"Impossible de parser le JSON final : {e}\nContenu : {raw_text}")

    # --- DEBUG JSON ---
    with open("/data-agent/debug_llm.json", "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=2, ensure_ascii=False)

    return final_json
