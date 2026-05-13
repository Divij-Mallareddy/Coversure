from config.settings import settings

def chunk_text(text: str, document_name: str) -> list[dict]:
    words = text.split()
    chunks = []
    
    i = 0
    while i < len(words):
        end = min(i + settings.CHUNK_SIZE, len(words))
        chunk_str = " ".join(words[i:end])
        chunks.append({
            "text": chunk_str,
            "document": document_name
        })
        
        i += (settings.CHUNK_SIZE - settings.CHUNK_OVERLAP)

    return chunks
