from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class ItemPedido(BaseModel):
    produto_id: str
    quantidade: int
    preco_unitario: float

class PayloadPedidoCriado(BaseModel):
    pedido_id: str
    cliente_id: str
    itens: List[ItemPedido]
    valor_total: float
    forma_pagamento: str
    timestamp_pedido: str

class Envelope(BaseModel):
    evento_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    evento_tipo: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    correlation_id: str
    versao_schema: str = "1.0"
    payload: dict