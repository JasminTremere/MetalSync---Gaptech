from fastapi import FastAPI
import os

app = FastAPI(title="MetalSync - Serviço de Pedidos")

@app.get("/health")
def health():
    return {"status": "ok", "servico": "pedido"}