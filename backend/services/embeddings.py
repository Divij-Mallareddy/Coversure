from sentence_transformers import SentenceTransformer
from config.settings import settings

# Load model once
model = SentenceTransformer(settings.EMBEDDING_MODEL)

def get_embeddings(texts: list[str]) -> list[list[float]]:
    # Generate embeddings utilizing the loaded model
    embeddings = model.encode(texts)
    return embeddings.tolist()
