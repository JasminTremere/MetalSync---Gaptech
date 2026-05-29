from fastapi import FastAPI
import os

app = FastAPI(title="MetalSync - Serviço de Logística")

@app.get("/health")
def health():
    return {"status": "ok", "servico": "logistica"}