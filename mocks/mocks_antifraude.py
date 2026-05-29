import pika
import time
import json
import random
import os

BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
TAXA_ANTIFRAUDE = float(os.getenv("TAXA_ANTIFRAUDE", "1"))

def callback(ch, method, properties, body):
    data = json.loads(body)
    correlation_id = data.get("correlation_id", "indefinido")
    
    # 90% aprovado, 10% bloqueado
    sorteio = random.random()
    if sorteio <= 0.90:
        evento_tipo = "pedido.aprovado_fraude"
    else:
        evento_tipo = "pedido.bloqueado_fraude"
        
    resposta = {
        "evento_id": str(random.randint(100000, 999999)),
        "evento_tipo": evento_tipo,
        "correlation_id": correlation_id,
        "payload": {"pedido_id": data.get("payload", {}).get("pedido_id")}
    }
    
    ch.basic_publish(
        exchange='',
        routing_key='antifraude.eventos',
        body=json.dumps(resposta)
    )
    print(f"[Antifraude] Processado: {evento_tipo} | ID: {correlation_id}")
    time.sleep(TAXA_ANTIFRAUDE)

# Conexão com o Broker
connection = pika.BlockingConnection(pika.ConnectionParameters(host=BROKER_HOST))
channel = connection.channel()

channel.queue_declare(queue='pedido.eventos')
channel.queue_declare(queue='antifraude.eventos')

channel.basic_consume(queue='pedido.eventos', on_message_callback=callback, auto_ack=True)

print("[Mock Antifraude] Aguardando eventos 'pedido.criado'...")
channel.start_consuming()