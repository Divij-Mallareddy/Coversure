from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services.pdf import extract_text_from_pdf
from services.chunking import chunk_text
from services.embeddings import get_embeddings
from services.vectorstore import single_store, multi_store
from services.rag import query_rag
from config.settings import settings
from knowledge_base.service import knowledge_base

router = APIRouter()

@router.post("/upload/")
async def upload_pdf(file: UploadFile = File(...), append: bool = Form(False)):
    mode = "memory" if append else "single"
    # 1. Extract text
    text = extract_text_from_pdf(file)
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    # 2. Chunking
    chunks = chunk_text(text, file.filename)
    
    # 3. Embeddings
    texts = [c["text"] for c in chunks]
    embeddings = get_embeddings(texts)

    # 4. Store
    if mode == "single":
        single_store.reset()
        single_store.add_chunks(chunks, embeddings)
        return {"message": "PDF processed successfully in single mode", "chunks": len(chunks)}
    else:
        multi_store.add_chunks(chunks, embeddings)
        return {"message": "PDF processed successfully in multi mode", "chunks": len(chunks)}

@router.post("/ask/")
async def ask_question(query: str):
    knowledge_chunks = knowledge_base.retrieve(query, top_k=settings.KNOWLEDGE_TOP_K)
    session_chunks = []
    session_mode = "single"

    if multi_store.index.ntotal > 0:
        store = multi_store
        session_mode = "memory"
    else:
        store = single_store

    if store.index.ntotal > 0:
        query_emb = get_embeddings([query])[0]
        session_chunks = store.search(query_emb, top_k=settings.TOP_K_RETRIEVAL)

    if not knowledge_chunks and not session_chunks:
        return {"error": "Knowledge base is empty or no relevant context was found."}

    retrieved_chunks = knowledge_chunks + session_chunks
    if knowledge_chunks and session_chunks:
        mode = "hybrid"
    elif knowledge_chunks:
        mode = "knowledge_base"
    else:
        mode = session_mode

    result = query_rag(query, retrieved_chunks, mode)
    result["retrieval"] = {
        "mode": mode,
        "knowledge_chunks": len(knowledge_chunks),
        "session_chunks": len(session_chunks),
        "min_knowledge_confidence": settings.KNOWLEDGE_MIN_CONFIDENCE,
    }
    
    return result

@router.post("/clear/")
async def clear_memory():
    single_store.reset()
    multi_store.reset()
    return {"message": "Memory cleared completely"}

@router.get("/knowledge/status")
async def knowledge_status():
    return knowledge_base.status()

@router.post("/knowledge/sync")
async def sync_knowledge():
    return knowledge_base.sync(use_cache=False)

@router.post("/knowledge/rebuild")
async def rebuild_knowledge():
    return knowledge_base.sync(force=True)
