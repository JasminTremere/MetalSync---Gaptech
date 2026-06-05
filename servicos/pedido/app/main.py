import threading
from fastapi import FastAPI
import os
import pymysql
import json
from consumer import iniciar_consumer, conectar_db
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MetalSync - Serviço de Pedidos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite requisições de qualquer origem (seu Live Server incluso)
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    t = threading.Thread(target=iniciar_consumer, daemon=True)
    t.start()

@app.get("/health")
def health():
    return {"status": "ok", "servico": "pedido"}

# No seu pedido/app/main.py
@app.get("/api/pedidos")
def listar_pedidos():
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM db_pedido_pedidos ORDER BY data_emissao DESC")
            pedidos = cursor.fetchall()
            # Converte itens_json de volta para objeto para o JS
            for p in pedidos:
                if p.get('itens_json'):
                    p['itens'] = json.loads(p['itens_json'])
            return pedidos
    finally:
        db.close()

@app.post("/api/novo-pedido")
def criar_pedido(payload: dict):
    # Print para debug - Olhe o terminal do seu VS Code/CMD após clicar no botão
    print("PAYLOAD RECEBIDO PELO FASTAPI:", payload)
    
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            # Usando .get(chave, valor_padrao) para evitar NULL se o campo não vier
            pedido_id = payload.get('pedido_id')
            cliente = payload.get('cliente')
            data = payload.get('data')
            horario = payload.get('horario', 'Não definido') # Padrão se vier nulo
            prioridade = payload.get('prioridade', 'Media')  # Padrão se vier nulo
            total = payload.get('total', 0)
            itens_json = payload.get('itens_json')

            sql = """
                INSERT INTO db_pedido_pedidos 
                (pedido_id, cliente, data_emissao, horario, prioridade, valor_total, itens_json, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'criado')
            """
            cursor.execute(sql, (pedido_id, cliente, data, horario, prioridade, total, itens_json))
            db.commit()
            return {"status": "sucesso"}
    except Exception as e:
        print("ERRO DETALHADO:", e)
        return {"status": "erro", "msg": str(e)}, 500
    finally:
        db.close()

# ROTA DE MÉTRICAS CORRIGIDA PARA O SEU BANCO REAL
@app.get("/metrics")
def metrics():
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            # Ajustado para db_pedido_pedidos
            cursor.execute("SELECT COUNT(*) as qtd FROM db_pedido_pedidos WHERE status='criado'")
            criados = cursor.fetchone()['qtd']
            cursor.execute("SELECT COUNT(*) as qtd FROM db_pedido_pedidos WHERE status='confirmado'")
            confirmados = cursor.fetchone()['qtd']
            cursor.execute("SELECT COUNT(*) as qtd FROM db_pedido_pedidos WHERE status='cancelado'")
            cancelados = cursor.fetchone()['qtd']
            
            # Ajustado para db_pedido_pedidos e coluna data_emissao
            cursor.execute("SELECT pedido_id, correlation_id, status, data_emissao FROM db_pedido_pedidos ORDER BY data_emissao DESC LIMIT 50")
            recentes = cursor.fetchall()
            
            for r in recentes:
                if r['data_emissao']:
                    # Converte a data/datetime para string para evitar erro de JSON
                    r['data_emissao'] = str(r['data_emissao'])
            
            return {
                "total_criados": criados,
                "total_confirmados": confirmados,
                "total_cancelados": cancelados,
                "total_entregues": confirmados,
                "pedidos_recentes": recentes
            }
    except Exception as e:
        return {"erro": str(e)}
    finally:
        db.close()

@app.get("/api/horarios-ocupados/{data}")
def listar_ocupados(data: str):
    db = conectar_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT horario FROM db_pedido_pedidos WHERE data_emissao = %s", (data,))
        resultados = cursor.fetchall()
        return [r['horario'] for r in resultados]