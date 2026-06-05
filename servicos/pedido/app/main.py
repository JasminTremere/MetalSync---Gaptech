import json
import threading
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from consumer import iniciar_consumer, conectar_db

app = FastAPI(title="MetalSync - Serviço de Pedidos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    t = threading.Thread(target=iniciar_consumer, daemon=True)
    t.start()

# --- HEALTH ---
@app.get("/health")
def health():
    return {"status": "ok", "servico": "pedido"}

# --- 1. CRIAR PEDIDO ---
@app.post("/api/novo-pedido")
def criar_pedido(payload: dict):
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            sql = """
                INSERT INTO db_pedido_pedidos
                    (pedido_id, cliente, data_emissao, horario, prioridade, valor_total, itens_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                payload.get('pedido_id'),
                payload.get('cliente'),
                payload.get('data'),
                payload.get('horario'),
                payload.get('prioridade'),
                payload.get('total'),
                payload.get('itens_json'),
            ))
            db.commit()
            print("Sucesso: Salvo no MySQL")
    except Exception as e:
        print(f"Erro banco: {e}")
        return {"status": "erro", "msg": str(e)}
    finally:
        db.close()

    # Disparo para o n8n
    # host.docker.internal resolve para o IP do seu PC a partir de dentro do container
    url_n8n = "http://host.docker.internal:5678/webhook/1aa06e03-1e82-4e6f-b1bf-99430b0cdb7b"
    try:
        resposta = requests.post(url_n8n, json=payload, timeout=5)
        print(f"Sucesso: Dados enviados ao n8n. Status: {resposta.status_code}")
    except Exception as e:
        print(f"Aviso: n8n não respondeu, mas o pedido foi salvo no banco: {e}")

    return {"status": "ok"}

# --- 2. LISTAR PEDIDOS ---
@app.get("/api/pedidos")
def listar_pedidos():
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT pedido_id, data_emissao, cliente, horario, prioridade, valor_total, itens_json
                FROM db_pedido_pedidos
                ORDER BY data_emissao DESC, horario ASC
            """
            cursor.execute(sql)
            resultados = cursor.fetchall()
            for r in resultados:
                if r['data_emissao']:
                    r['data_emissao'] = str(r['data_emissao'])
                r['itens'] = json.loads(r['itens_json']) if r['itens_json'] else []
            return {"pedidos": resultados}
    except Exception as e:
        print(f"Erro ao listar pedidos: {e}")
        return {"erro": str(e)}
    finally:
        db.close()

# --- 3. LISTAR CLIENTES ---
@app.get("/api/clientes")
def listar_clientes():
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT DISTINCT cliente
                FROM db_pedido_pedidos
                WHERE cliente IS NOT NULL AND cliente != ''
                ORDER BY cliente
            """
            cursor.execute(sql)
            return {"clientes": [r['cliente'] for r in cursor.fetchall()]}
    except Exception as e:
        return {"erro": str(e)}
    finally:
        db.close()

# --- 4. HORÁRIOS OCUPADOS ---
@app.get("/api/horarios-ocupados")
def get_horarios_ocupados(data: str):
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            sql = """
                SELECT pedido_id, horario
                FROM db_pedido_pedidos
                WHERE data_emissao = %s
            """
            cursor.execute(sql, (data,))
            resultados = cursor.fetchall()
            return {"pedidos": resultados}
    except Exception as e:
        return {"erro": str(e)}
    finally:
        db.close()

# --- 5. MOVER PEDIDO ---
@app.post("/api/mover-pedido")
def mover_pedido(payload: dict):
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            sql = "UPDATE db_pedido_pedidos SET horario = %s WHERE pedido_id = %s"
            cursor.execute(sql, (payload.get('novo_horario'), payload.get('pedido_id')))
            db.commit()
            return {"status": "sucesso"}
    except Exception as e:
        db.rollback()
        return {"erro": str(e)}
    finally:
        db.close()

# --- 6. ATUALIZAR PEDIDO ---
@app.post("/api/atualizar-pedido")
def atualizar_pedido(payload: dict):
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            sql = "UPDATE db_pedido_pedidos SET data_emissao = %s, horario = %s WHERE pedido_id = %s"
            cursor.execute(sql, (payload.get('data'), payload.get('horario'), payload.get('pedido_id')))
            db.commit()
            return {"status": "sucesso"}
    except Exception as e:
        db.rollback()
        print("Dados recebidos:", payload)
        return {"erro": str(e)}
    finally:
        db.close()

# --- 7. MÉTRICAS ---
@app.get("/metrics")
def metrics():
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as qtd FROM db_pedido_pedidos WHERE status='criado'")
            criados = cursor.fetchone()['qtd']

            cursor.execute("SELECT COUNT(*) as qtd FROM db_pedido_pedidos WHERE status='confirmado'")
            confirmados = cursor.fetchone()['qtd']

            cursor.execute("SELECT COUNT(*) as qtd FROM db_pedido_pedidos WHERE status='cancelado'")
            cancelados = cursor.fetchone()['qtd']

            cursor.execute("""
                SELECT pedido_id, correlation_id, status, data_emissao
                FROM db_pedido_pedidos
                ORDER BY data_emissao DESC
                LIMIT 50
            """)
            recentes = cursor.fetchall()
            for r in recentes:
                if r['data_emissao']:
                    r['data_emissao'] = str(r['data_emissao'])

            return {
                "total_criados": criados,
                "total_confirmados": confirmados,
                "total_cancelados": cancelados,
                "pedidos_recentes": recentes,
            }
    except Exception as e:
        return {"erro": str(e)}
    finally:
        db.close()