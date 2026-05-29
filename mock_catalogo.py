from fastapi import FastAPI

app = FastAPI(title="MetalSync – Serviço de Logística", version="1.0.0")


@app.get("/health")
async def health():
    return {"status": "ok", "servico": "logistica"}
