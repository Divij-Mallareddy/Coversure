import faiss
import numpy as np

class VectorStore:
    def __init__(self, dimension: int = 384): # all-MiniLM-L6-v2 output dimension is 384
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = [] # stores dicts {"text": "...", "document": "..."}

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]]):
        embeddings_np = np.array(embeddings, dtype=np.float32)
        self.index.add(embeddings_np)
        self.metadata.extend(chunks)

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        if self.index.ntotal == 0:
            return []
            
        q_emb = np.array([query_embedding], dtype=np.float32)
        distances, indices = self.index.search(q_emb, top_k)
        
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx < len(self.metadata):
                result = dict(self.metadata[idx])
                confidence = float(1 / (1 + max(0, distance)))
                result["score"] = confidence
                result["confidence"] = confidence
                result["source_type"] = "uploaded_document"
                results.append(result)
        return results
        
    def reset(self):
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []

# Instantiate our stores
# For 'single' mode
single_store = VectorStore()

# For 'multi' mode
multi_store = VectorStore()
