from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid
import io
from PyPDF2 import PdfReader
import json
from datetime import datetime
import os

# --- Imports pipeline COPIL ---
from app.debug_tools import debug_wrap
from app.file_finder import find_latest_budget_file
from app.excel_parser import parse_excel
from app.llm_agent import generate_copil_text
from app.ppt_generator import generate_ppt_from_excel



app = FastAPI()

# --- Config ---
OLLAMA_URL = "http://ollama-agent:11434"   # FIXED
OLLAMA_MODEL = "llama3.2:1b"
QDRANT_URL = "http://qdrant-agent:6333"
COLLECTION_NAME = "anomalies"
EMBEDDING_DIM = 384
DATA_DIR = "/data-agent"                  # FIXED (chemin local)

# --- Session state ---
LAST_INGEST = False

# --- Clients ---
qdrant = QdrantClient(url=QDRANT_URL)
embedder = SentenceTransformer("all-MiniLM-L6-v2")


# --- Init collection ---
def init_collection():
    collections = qdrant.get_collections().collections
    names = [c.name for c in collections]
    if COLLECTION_NAME not in names:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )

@app.on_event("startup")
async def startup_event():
    init_collection()


# --- Utils ---

def embed_text(text: str):
    return embedder.encode(text).tolist()

def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)

def chunk_text(text: str, max_chars: int = 200):
    chunks = []
    current = []
    length = 0
    for line in text.splitlines():
        if length + len(line) > max_chars and current:
            chunks.append("\n".join(current))
            current = []
            length = 0
        current.append(line)
        length += len(line)
    if current:
        chunks.append("\n".join(current))
    return chunks


# --- Models ---
class PromptInput(BaseModel):
    prompt_template: str


# --- Endpoints ---

@app.post("/ingest_anomaly")
async def ingest_anomaly(file: UploadFile = File(...)):
    global LAST_INGEST
    LAST_INGEST = True

    content = await file.read()

    if file.filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf(content)
    else:
        text = content.decode("utf-8", errors="ignore")

    chunks = chunk_text(text)

    points = []
    for chunk in chunks:
        vec = embed_text(chunk)
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={"text": chunk, "source": file.filename},
            )
        )

    if points:
        qdrant.upsert(collection_name=COLLECTION_NAME, points=points)

    return {"status": "ok", "chunks": len(points)}



@app.post("/generate_plan")
def generate_plan(data: PromptInput):
    global LAST_INGEST

    if not LAST_INGEST:
        search_result = []
        context = ""
    else:
        search_result = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=[0] * EMBEDDING_DIM,
            limit=5,
            with_payload=True
        )

        context_chunks = [
            hit.payload["text"]
            for hit in search_result
            if "text" in hit.payload
        ]

        context = "\n\n---\n\n".join(context_chunks) if context_chunks else ""

    used_chunks = [
        {
            "score": hit.score,
            "text": hit.payload["text"],
            "source": hit.payload.get("source", "unknown")
        }
        for hit in search_result
        if "text" in hit.payload
    ]

    try:
        prompt = data.prompt_template.format(context=context)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur format prompt: {str(e)}")

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Ollama error: {response.text}")

    result = response.json()

    return {
        "response": result.get("response", ""),
        "context_used": len(used_chunks),
        "chunks": used_chunks
    }



@app.post("/reset_qdrant")
def reset_qdrant():
    try:
        qdrant.delete_collection(COLLECTION_NAME)
        qdrant.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)
        )
        return {"status": "ok", "message": "Qdrant vidé."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/reset_session")
def reset_session():
    global LAST_INGEST
    LAST_INGEST = False
    return {"status": "ok", "message": "Session réinitialisée."}


@app.get("/debug/qdrant")
def debug_qdrant():
    result = qdrant.scroll(
        collection_name=COLLECTION_NAME,
        limit=5,
        with_payload=True
    )
    return result


# --- PIPELINE COPIL (Excel + LLM + PPT) ---

@debug_wrap
@app.post("/agent/ppt")
def generate_ppt_agent():
    try:
        # 1) Trouver le fichier Excel
        excel_path = find_latest_budget_file(DATA_DIR)
        print(f"[DEBUG] excel_path = {excel_path}")

        with open("/data-agent/debug_excel_info.txt", "w", encoding="utf-8") as f:
            f.write(f"excel_path = {excel_path}\n")

        # 2) Parser l'Excel
        context = parse_excel(excel_path)
        with open("/data-agent/debug_context.json", "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

        # 3) Appel LLM (RAW pour debug)
        raw_llm = generate_copil_text(context, return_raw=True)

        # 4) Appel LLM (JSON final)
        llm_output = generate_copil_text(context, return_raw=False)

        # 5) Répertoire de sortie (déjà existant)
        OUTPUT_DIR = "/data-agent/output"

        # 6) Nom horodaté
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"COPIL_{timestamp}.pptx"
        output_path = os.path.join(OUTPUT_DIR, filename)

        # 7) Génération PPT
        generate_ppt_from_excel(excel_path, output_path, llm_output=llm_output)

        # 8) Retour du fichier
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=filename,
        )

    except Exception as e:
        print(f"[ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))
