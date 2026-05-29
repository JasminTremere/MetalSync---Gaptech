import pika
import time
import json
import random
import os

BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
TAXA_CATALOGO = float(os.getenv("TAXA_CATALOGO", "1"))

def callback(ch, method, properties, body):
    data = json.loads(body)
    if data.get("evento_tipo") == "pedido.confirmado":
        correlation_id = data.get("correlation_id", "indefinido")
        
        atualizacao = {
            "evento_id": str(random.randint(100000, 999999)),
            "evento_tipo": "estoque.atualizado",
            "correlation_id": correlation_id,
            "payload": {"status": "pecas_vinculadas_ao_catalogo_gaptech"}
        }
        
        ch.basic_publish(
            exchange='',
            routing_key='catalogo.eventos',
            body=json.dumps(atualizacao)
        )
        print(f"[Catálogo Gaptech] Estoque atualizado para ID: {correlation_id}")
        time.sleep(TAXA_CATALOGO)

connection = pika.BlockingConnection(pika.ConnectionParameters(host=BROKER_HOST))
channel = connection.channel()

channel.queue_declare(queue='pedido.eventos')
channel.queue_declare(queue='catalogo.eventos')

channel.basic_consume(queue='pedido.eventos', on_message_callback=callback, auto_ack=True)

print("[Mock Catálogo] Aguardando eventos 'pedido.confirmado'...")
channel.start_consuming()