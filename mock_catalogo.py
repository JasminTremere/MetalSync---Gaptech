# mock_catalogo.py – MetalSync/GAPTECH | pedido.confirmado → estoque.atualizado
import json
import os

import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

FILA_ENTRADA = "pedido.confirmado"
FILA_SAIDA = "estoque.atualizado"
EXCHANGE = "metalsync"
# Catálogo de peças – GAPTECH Usinagem e Ferramentaria
CATALOGO = {
    "GAP-001": {"descricao": "Bucha de Bronze Usinada Ø50mm",    "estoque": 120},
    "GAP-002": {"descricao": "Eixo Escalonado Aço 1045",         "estoque": 85},
    "GAP-003": {"descricao": "Flange Inox 316 DN80",             "estoque": 40},
    "GAP-004": {"descricao": "Pinhão Helicoidal M3 Z28",         "estoque": 60},
    "GAP-005": {"descricao": "Tampa de Redutor FC250",           "estoque": 30},
    "GAP-006": {"descricao": "Barra Chata Aço 1020 25x6mm",     "estoque": 200},
    "GAP-007": {"descricao": "Placa de Fixação Retificada",      "estoque": 15},
    "GAP-008": {"descricao": "Porca Sextavada DIN934 M24 Inox", "estoque": 500},
}


def conectar():
    credenciais = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credenciais,
        heartbeat=60, blocked_connection_timeout=30,
    )
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    for fila in (FILA_ENTRADA, FILA_SAIDA):
        ch.queue_declare(queue=fila, durable=True)
        ch.queue_bind(queue=fila, exchange=EXCHANGE, routing_key=fila)
    return conn, ch

def processar(ch, method, _props, body):
    pedido = json.loads(body)
    itens = pedido.get("itens", [])
    atualizacoes = []
    for item in itens:
        cod = item.get("codigo_peca", "")
        qty = int(item.get("quantidade", 1))
        if cod in CATALOGO:
            CATALOGO[cod]["estoque"] = max(0, CATALOGO[cod]["estoque"] - qty)
            atualizacoes.append({
                "codigo": cod,
                "descricao": CATALOGO[cod]["descricao"],
                "estoque_atual": CATALOGO[cod]["estoque"],
            })
    evento = {"pedido_id": pedido.get("id"), "atualizacoes": atualizacoes}
    ch.basic_publish(
        exchange=EXCHANGE, routing_key=FILA_SAIDA,
        body=json.dumps(evento),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    print(f"[catalogo] pedido {pedido.get('id', '?')} → {len(atualizacoes)} peça(s) atualizada(s)")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    print("[catalogo] Iniciando mock GAPTECH…")
    conn, ch = conectar()
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=FILA_ENTRADA, on_message_callback=processar)
    print(f"[catalogo] Aguardando mensagens em '{FILA_ENTRADA}'…")
    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        ch.stop_consuming()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
