import pika
import json
import os
import pymysql
from models import Envelope

def conectar_db():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )

def registrar_evento_processado(cursor, evento_id):
    cursor.execute(
        "INSERT INTO eventos_processados (evento_id, processado_em) VALUES (%s, NOW())",
        (evento_id,)
    )

def processar_saga(ch, method, properties, body):
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            envelope_dict = json.loads(body)
            try:
                envelope = Envelope(**envelope_dict)
            except Exception as err:
                print(f" [⚠️ Schema Inválido] Logado e descartado: {err}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            cursor.execute("SELECT 1 FROM eventos_processados WHERE evento_id = %s", (envelope.evento_id,))
            if cursor.fetchone():
                print(f" [🔄 Idempotência] Evento duplicado ignorado: {envelope.evento_id}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            payload = envelope.payload
            corr_id = envelope.correlation_id
            tipo = envelope.evento_tipo

            if tipo in ["pagamento.aprovado", "pagamento.recusado"]:
                pagamento_ok = 1 if tipo == "pagamento.aprovado" else 0
                cursor.execute(
                    "UPDATE db_pedido_pedidos SET pagamento_ok = %s WHERE correlation_id = %s",
                    (pagamento_ok, corr_id)
                )
            
            elif tipo in ["pedido.aprovado_fraude", "pedido.bloqueado_fraude"]:
                fraude_ok = 1 if tipo == "pedido.aprovado_fraude" else 0
                cursor.execute(
                    "UPDATE db_pedido_pedidos SET fraude_ok = %s WHERE correlation_id = %s",
                    (fraude_ok, corr_id)
                )

            cursor.execute(
                "SELECT pedido_id, pagamento_ok, fraude_ok, status FROM db_pedido_pedidos WHERE correlation_id = %s",
                (corr_id,)
            )
            pedido = cursor.fetchone()

            if pedido and pedido['status'] == "criado":
                p_ok = pedido['pagamento_ok']
                f_ok = pedido['fraude_ok']

                if p_ok is not None and f_ok is not None:
                    novo_status = "confirmado" if (p_ok == 1 and f_ok == 1) else "cancelado"
                    cursor.execute(
                        "UPDATE pedidos SET status = %s WHERE correlation_id = %s",
                        (novo_status, corr_id)
                    )
                    
                    evento_final = Envelope(
                        evento_tipo=f"pedido.{novo_status}",
                        correlation_id=corr_id,
                        payload={"pedido_id": pedido['pedido_id'], "status": novo_status}
                    )
                    
                    ch.basic_publish(
                        exchange='',
                        routing_key='pedido.eventos',
                        body=json.dumps(evento_final.dict()),
                        properties=pika.BasicProperties(delivery_mode=2)
                    )
                    print(f" [🎯 Saga Concluída] Pedido {pedido['pedido_id']} alterado para {novo_status.upper()}")

            registrar_evento_processado(cursor, envelope.evento_id)
            db.commit()
    except Exception as e:
        print(f" [x] Erro no processamento da saga: {e}")
        db.rollback()
    finally:
        db.close()
        ch.basic_ack(delivery_tag=method.delivery_tag)

# Garanta que o nome da função abaixo esteja escrito EXATAMENTE assim:
def iniciar_consumer():
    credenciais = pika.PlainCredentials('gaptech', 'gaptech_suporte')
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=os.getenv("BROKER_HOST", "rabbitmq"), credentials=credenciais)
    )
    channel = connection.channel()
    
    channel.queue_declare(queue='pagamento.eventos', durable=True)
    channel.queue_declare(queue='antifraude.eventos', durable=True)
    channel.queue_declare(queue='pedido.eventos', durable=True)

    channel.basic_consume(queue='pagamento.eventos', on_message_callback=processar_saga)
    channel.basic_consume(queue='antifraude.eventos', on_message_callback=processar_saga)
    
    print(' [*] Serviço Pedido escutando canais assíncronos da Saga...')
    channel.start_consuming()