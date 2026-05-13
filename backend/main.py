from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.api import router
from knowledge_base.service import knowledge_base
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Insurance Policy RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.on_event("startup")
async def sync_knowledge_base():
    knowledge_base.sync()

@app.get("/")
def read_root():
    return {"message": "Insurance Policy RAG Backend running."}
