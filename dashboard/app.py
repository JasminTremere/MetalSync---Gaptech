import os
import json
import pika
import pymysql
from dotenv import load_dotenv
import streamlit as st
load_dotenv()

# Conexão com o Banco de Dados da HostGator
def conectar_banco():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )

# Cérebro da IA: Analisa o pedido e decide a alíquota fiscal comercial
def inteligenca_artificial_fiscal(cliente, produto, valor_total):
    """
    Aqui entra a lógica de classificação. 
    Se o cliente for corporativo/indústria de grande porte (ex: autopeças, metalúrgicas),
    a IA classifica como IOB (6%). Se for varejo ou pedidos pulverizados de Cidades, entra como NF-e (12%).
    """
    # Exemplo de regra inteligente/heurística de IA para o ecossistema Gaptech:
    if valor_total > 5000 or "SA" in cliente.upper() or "LTDA" in cliente.upper():
        return "IOB (6%)"
    else:
        return "NF-e Cidades (12%)"

def processar_faturamento(ch, method, properties, body):
    pedido = json.loads(body)
    print(f" [os] Processando faturamento do pedido: {pedido['pedido_id']}")
    
    # 1. Executa a Inteligência Artificial para decidir a regra fiscal
    regra_escolhida = inteligenca_artificial_fiscal(
        cliente=pedido.get('cliente', ''),
        produto=pedido.get('produto', ''),
        valor_total=float(pedido.get('valor_total', 0))
    )
    
    # 2. Salva o resultado direto na tabela 'faturamento' da HostGator
    db = conectar_banco()
    try:
        with db.cursor() as cursor:
            sql = """
                INSERT INTO faturamento (pedido_id, valor_faturado, regra_fiscal, status_faturamento)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (
                pedido['pedido_id'], 
                pedido['valor_total'], 
                regra_escolhida, 
                'concluido'
            ))
        db.commit()
        print(f" [v] Faturamento salvo no MySQL com a regra: {regra_escolhida}")
    except Exception as e:
        print(f" [x] Erro ao salvar no banco: {e}")
    finally:
        db.close()

    ch.basic_ack(delivery_tag=method.delivery_tag)

# Configuração do Consumidor RabbitMQ
def iniciar_consumidor():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=os.getenv("BROKER_HOST", "rabbitmq")))
    channel = connection.channel()
    
    channel.queue_declare(queue='fila_pedidos', durable=True)
    channel.basic_consume(queue='fila_pedidos', on_message_callback=processar_faturamento)
    
    print(' [*] Aguardando mensagens de pedidos para faturar. Para sair pressione CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    iniciar_consumidor()