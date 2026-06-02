import requests
import time
import random
import uuid
import argparse
from datetime import datetime

# Configuração dos argumentos exigidos pelo guião do Módulo 3
parser = argparse.ArgumentParser(description="Gerador de Carga ShopFlow")
parser.add_argument("--total", type=int, default=20, help="Número total de pedidos a criar")
parser.add_argument("--taxa", type=int, default=2, help="Pedidos por segundo")
args = parser.parse_args()

URL_API = "http://localhost:8001/pedidos"  # Endpoint do Serviço Pedido exposto no teu Docker

FORMAS_PAGAMENTO = ["cartao_credito", "pix", "boleto"]
PRODUTOS_EXEMPLO = ["Chapa de Aço H13", "Barra Redonda SAE 1045", "Perfil U Dobrado", "Bloco de Usinagem CNC"]

print(f"🚀 Iniciando Gerador: {args.total} pedidos com taxa de {args.taxa} por segundo...\n")

for i in range(args.total):
    pedido_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    cliente_id = f"CLI-{random.randint(1000, 9999)}"
    
    # Regra: Pelo menos 1 item, valor unitário aleatório
    itens = []
    num_itens = random.randint(1, 3)
    valor_total = 0.0
    
    for _ in range(num_itens):
        preco = round(random.uniform(20.0, 700.0), 2)
        qtd = random.randint(1, 2)
        valor_total += (preco * qtd)
        itens.append({
            "produto_id": random.choice(PRODUTOS_EXEMPLO),
            "quantidade": qtd,
            "preco_unitario": preco
        })
    
    # Garante que o valor total fique dentro do limite de teste (entre R$ 20 e R$ 2000)
    valor_total = round(min(max(valor_total, 20.0), 2000.0), 2)

    # Montagem do payload estruturado conforme o Documento de Referência
    payload_evento = {
        "evento_id": str(uuid.uuid4()),
        "evento_tipo": "pedido.criado",
        "timestamp": datetime.utcnow().isoformat(),
        "correlation_id": correlation_id,
        "versao_schema": "1.0",
        "payload": {
            "pedido_id": pedido_id,
            "cliente_id": cliente_id,
            "itens": itens,
            "valor_total": valor_total,
            "forma_pagamento": random.choice(FORMAS_PAGAMENTO),
            "timestamp_pedido": datetime.utcnow().isoformat()
        }
    }

    # Envia o POST para a API do Serviço Pedido
    try:
        response = requests.post(URL_API, json=payload_evento, timeout=2)
        if response.status_code in [200, 201]:
            print(f" [✓] Pedido {i+1}/{args.total} enviado! ID: {pedido_id[:6]}... | Total: R$ {valor_total} | CorrelationID: {correlation_id[:6]}")
        else:
            print(f" [⚠️] Erro ao enviar pedido: HTTP {response.status_code}")
    except Exception as e:
        print(f" [x] Falha na conexão com a API de Pedidos: {e}")

    # Controla a taxa de envio (ex: taxa 2 = 1/2 segundo de pausa)
    time.sleep(1.0 / args.taxa)

print("\n🏁 Envio de carga finalizado com sucesso!")