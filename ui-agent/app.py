import gradio as gr
import requests
import json
import tempfile
import os

API_INGEST_URL = "http://fastapi-backend:8000/ingest_anomaly"
API_PLAN_URL = "http://fastapi-backend:8000/generate_plan"
API_RESET_QDRANT = "http://fastapi-backend:8000/reset_qdrant"
API_RESET_SESSION = "http://fastapi-backend:8000/reset_session"
API_PPT_URL = "http://fastapi-backend-agent:8000/agent/ppt"   # <--- AJOUT


# --- 1) Ingestion du fichier ---
def ingest_file(file):
    if file is None:
        return "Aucun fichier fourni."

    try:
        with open(file, "rb") as f:
            files = {
                "file": (file, f.read(), "application/octet-stream")
            }

        r = requests.post(API_INGEST_URL, files=files, timeout=30)

        if r.status_code != 200:
            return f"Erreur ingestion : {r.text}"

        data = r.json()
        return json.dumps(data, indent=2, ensure_ascii=False)

    except Exception as e:
        return f"Erreur interne UI : {str(e)}"



# --- 2) Génération via RAG ---
def generate_plan(prompt):
    if not prompt.strip():
        return "Merci de saisir un prompt.", None, None

    try:
        payload = {
            "prompt_template": prompt
        }

        r = requests.post(API_PLAN_URL, json=payload)

        if r.status_code != 200:
            return f"Erreur génération : {r.text}", None, None

        data = r.json()

        chunks = data.get("chunks", [])
        table = []

        for c in chunks:
            table.append([
                c.get("score", ""),
                c.get("text", ""),
                c.get("source", "")
            ])

        return data.get("response", ""), data.get("context_used", 0), table

    except Exception as e:
        return f"Erreur interne UI : {str(e)}", None, None



# --- 3) Reset Qdrant ---
def reset_qdrant():
    try:
        r = requests.post(API_RESET_QDRANT)
        return r.json().get("message", "Réinitialisation effectuée.")
    except Exception as e:
        return f"Erreur reset Qdrant : {str(e)}"


# --- 4) Reset Session ---
def reset_session():
    try:
        r = requests.post(API_RESET_SESSION)
        return r.json().get("message", "Session réinitialisée.")
    except Exception as e:
        return f"Erreur reset session : {str(e)}"



# --- 5) NOUVEAU : Génération PPT ---
def generate_ppt():
    try:
        r = requests.post(API_PPT_URL)

        if r.status_code != 200:
            return None, f"Erreur génération PPT : {r.text}"

        # Récupérer le nom réel du fichier depuis le header
        dispo = r.headers.get("content-disposition", "")
        filename = "COPIL_Agent.pptx"

        if "filename=" in dispo:
            filename = dispo.split("filename=")[-1].strip('"')

        # Écrire le fichier dans un fichier temporaire
        tmp_path = os.path.join(tempfile.gettempdir(), filename)
        with open(tmp_path, "wb") as f:
            f.write(r.content)

        # Gradio attend un chemin vers un fichier
        return tmp_path, "PPT généré avec succès."

    except Exception as e:
        return None, f"Erreur interne UI : {str(e)}"




# --- Interface Gradio ---
with gr.Blocks(title="RAG - Générateur de plan de test") as demo:

    gr.Markdown("## 📥 Ingestion d’un fichier d’anomalie")
    file_input = gr.File(label="Dépose ton fichier d'anomalie (txt ou pdf)")
    ingest_btn = gr.Button("Ingest dans Qdrant")
    ingest_output = gr.Textbox(label="Résultat ingestion")

    ingest_btn.click(fn=ingest_file, inputs=file_input, outputs=ingest_output)


    # --- Reset ---
    gr.Markdown("## 🔄 Réinitialisation")

    reset_qdrant_btn = gr.Button("Reset Qdrant (vider la base)")
    reset_session_btn = gr.Button("Reset Session (LAST_INGEST = False)")

    reset_qdrant_output = gr.Textbox(label="Résultat Reset Qdrant")
    reset_session_output = gr.Textbox(label="Résultat Reset Session")

    reset_qdrant_btn.click(reset_qdrant, None, reset_qdrant_output)
    reset_session_btn.click(reset_session, None, reset_session_output)


    # --- Prompt ---
    gr.Markdown("## 🧠 Prompt")

    prompt_input = gr.Textbox(
        label="Prompt",
        placeholder="Écris ici ton prompt contenant {context}"
    )

    plan_btn = gr.Button("Générer la réponse")

    plan_output = gr.Markdown(label="🧠 Réponse générée")
    context_output = gr.Number(label="Chunks utilisés")
    chunks_output = gr.Dataframe(
        headers=["score", "text", "source"],
        label="📚 Chunks utilisés",
        wrap=True,
        interactive=False
    )

    plan_btn.click(
        fn=generate_plan,
        inputs=[prompt_input],
        outputs=[plan_output, context_output, chunks_output]
    )


    # --- NOUVEAU : Génération PPT ---
    gr.Markdown("## 📊 Génération automatique du PPT COPIL")

    ppt_btn = gr.Button("Générer le PPT de la semaine")
    ppt_file = gr.File(label="Télécharger le PPT")
    ppt_status = gr.Textbox(label="Statut")

    ppt_btn.click(
        fn=generate_ppt,
        inputs=None,
        outputs=[ppt_file, ppt_status]
    )


demo.launch(server_name="0.0.0.0", server_port=7860, debug=True)
