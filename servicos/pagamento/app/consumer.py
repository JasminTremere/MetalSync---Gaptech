import os
import json
import pika
import pymysql
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Inicializa o cliente da IA da Google usando a chave do .env
client_ia = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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

# Cérebro da IA: Analisa a descrição e retorna a regra fiscal em JSON estruturado
def inteligenca_artificial_fiscal(descricao_vale):
    prompt = f"""
    Você é o Agente de Classificação Fiscal da Gaptech. 
    Analise a descrição do vale abaixo e classifique a natureza do serviço com base estrita nestas regras de negócio:

    Regra 1: Se o texto descrever usinagem, produção em lote ou reposição padrão, classifique como 'IOB', defina a aliquota como 0.06 e a rota como 'industrializacao'.
    Regra 2: Se o texto descrever manutenção customizada, serviços externos ou demandas sazonais exclusivas, classifique como 'NF-E CIDADES', defina a aliquota como 0.12 e a rota como 'servicos'.

    Texto para análise: "{descricao_vale}"

    Responda ESTREITAMENTE em formato JSON com a seguinte estrutura (não adicione nenhuma palavra antes ou depois do JSON):
    {{
        "classificacao": "IOB ou NF-E CIDADES",
        "aliquota": 0.06 ou 0.12,
        "rota": "industrializacao ou servicos"
    }}
    """
    
    try:
        # Usando o modelo mais rápido e econômico do Gemini para classificação (gemini-2.5-flash)
        response = client_ia.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json" # Força o Gemini a devolver um JSON perfeito
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f" [x] Falha na IA, usando fallback de segurança: {e}")
        return {"classificacao": "NF-E CIDADES", "aliquota": 0.12, "rota": "servicos"}

def processar_faturamento(ch, method, properties, body):
    try:
        # 1. Escuta o evento que veio do RabbitMQ
        pedido = json.loads(body)
        descricao = pedido.get('descricao_vale', pedido.get('produto', 'Produção em lote padrão'))
        valor_total = float(pedido.get('valor_total', pedido.get('total', 0)))
        
        print(f" [🤖 Chamando IA] Analisando descrição: '{descricao}'")
        
        # 2. IA analisa e toma a decisão baseada nas regras secretas da Gaptech
        resultado_ia = inteligenca_artificial_fiscal(descricao)
        
        classificacao = resultado_ia["classificacao"]
        aliquota = resultado_ia["aliquota"]
        rota_faturamento = resultado_ia["rota"]
        
        # 3. Agente de Cálculo: Calcula o valor do imposto retido
        imposto_retido = round(valor_total * aliquota, 2)
        
        print(f" [➔ IA Decidiu] Classe: {classificacao} | Alíquota: {aliquota*100}% | Imposto: R$ {imposto_retido}")
        
        # 4. Salva o resultado direto na HostGator
        db = conectar_banco()
        with db.cursor() as cursor:
            # Salvando na tabela que criamos
            sql = """
                INSERT INTO faturamento (pedido_id, valor_faturado, regra_fiscal, status_faturamento)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (
                pedido.get('pedido_id'), 
                valor_total, 
                f"{classificacao} ({int(aliquota*100)}%)", 
                'concluido'
            ))
        db.commit()
        db.close()
        
        # 5. Publica de volta no broker o evento de aprovação para os próximos microsserviços
        evento_aprovado = {
            "pedido_id": pedido.get('pedido_id'),
            "status": "pagamento.aprovado",
            "imposto_retido": imposto_retido,
            "rota_utilizada": rota_faturamento
        }
        
        ch.basic_publish(
            exchange='',
            routing_key='fila_logistica', # Envia para a fila da logística trabalhar
            body=json.dumps(evento_aprovado),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        print(f" [✓] Evento 'pagamento.aprovado' enviado para a fila de logística!")
        
    except Exception as e:
        print(f" [x] Erro no processamento completo: {e}")
        
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def iniciar_consumidor():
    # SUBSTUIÇÃO AQUI: Garante que a conexão use as credenciais corretas do broker
    credenciais = pika.PlainCredentials('gaptech', 'gaptech_suporte')
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=os.getenv("BROKER_HOST", "rabbitmq"), credentials=credenciais)
    )
    
    channel = connection.channel()
    
    # Escuta a fila configurada
    channel.queue_declare(queue='fila_pedidos', durable=True)
    channel.queue_declare(queue='fila_logistica', durable=True) # Garante que a fila de destino exista
    
    channel.basic_consume(queue='fila_pedidos', on_message_callback=processar_faturamento)
    print(' [*] IA de Faturamento ativa na escuta do RabbitMQ...')
    channel.start_consuming()

if __name__ == '__main__':
    iniciar_consumidor()