"""
mock_antifraude.py – MetalSync / GAPTECH
Consome: pedido.criado
Publica:  pedido.aprovado_fraude (90 %) | pedido.bloqueado_fraude (10 %)
Taxa:     TAXA_ANTIFRAUDE eventos/segundo (padrão = 1)
"""
import json
import os
import random
import time

import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
TAXA = float(os.getenv("TAXA_ANTIFRAUDE", 1))
PROB_APROVACAO = float(os.getenv("PROB_APROVACAO_FRAUDE", 0.90))

FILA_ENTRADA = "pedido.criado"
FILA_APROVADO = "pedido.aprovado_fraude"
FILA_BLOQUEADO = "pedido.bloqueado_fraude"
EXCHANGE = "metalsync"


def conectar():
    credenciais = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credenciais,
        heartbeat=60, blocked_connection_timeout=30,
    )
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    for fila in (FILA_ENTRADA, FILA_APROVADO, FILA_BLOQUEADO):
        ch.queue_declare(queue=fila, durable=True)
        ch.queue_bind(queue=fila, exchange=EXCHANGE, routing_key=fila)
    return conn, ch


def processar(ch, method, _props, body):
    pedido = json.loads(body)
    destino = FILA_APROVADO if random.random() < PROB_APROVACAO else FILA_BLOQUEADO
    resultado = {**pedido, "resultado_antifraude": destino.split(".")[1]}
    ch.basic_publish(
        exchange=EXCHANGE, routing_key=destino,
        body=json.dumps(resultado),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    print(f"[antifraude] pedido {pedido.get('id', '?')} → {destino}")
    ch.basic_ack(delivery_tag=method.delivery_tag)
    time.sleep(1.0 / TAXA)


def main():
    print("[antifraude] Iniciando mock…")
    conn, ch = conectar()
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=FILA_ENTRADA, on_message_callback=processar)
    print(f"[antifraude] Aguardando mensagens em '{FILA_ENTRADA}'…")
    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        ch.stop_consuming()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
