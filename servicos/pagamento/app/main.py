from fastapi import FastAPI
import threading
import os
from consumer import iniciar_consumidor  # Importa o operário da IA que criamos no arquivo ao lado

app = FastAPI(title="MetalSync - Serviço de Pagamentos")

@app.get("/health")
def health():
    return {"status": "ok", "servico": "pagamento"}

# Evento mágico que liga o operário do RabbitMQ em background assim que o container sobe
@app.on_event("startup")
def startup_event():
    threading.Thread(target=iniciar_consumidor, daemon=True).start()