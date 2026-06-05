import json
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Certifique-se de que estes imports existem no seu arquivo original
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

@app.get("/health")
def health():
    return {"status": "ok", "servico": "pedido"}

# --- ROTA LISTAR PEDIDOS ---
@app.get("/api/pedidos")
def listar_pedidos():
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            # Padronizado para 'hora'
            sql = "SELECT pedido_id, data_emissao, cliente, hora, prioridade, valor_total, itens_json FROM db_pedido_pedidos ORDER BY data_emissao DESC"
            cursor.execute(sql)
            resultados = cursor.fetchall()

            for r in resultados:
                if r['data_emissao']: r['data_emissao'] = str(r['data_emissao'])
                r['itens'] = json.loads(r['itens_json']) if r['itens_json'] else []
            return {"pedidos": resultados}
    except Exception as e:
        return {"erro": str(e)}, 500
    finally:
        db.close()

# --- ROTA LISTAR CLIENTES ---
@app.get("/api/clientes")
def listar_clientes():
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            sql = "SELECT DISTINCT cliente FROM db_pedido_pedidos WHERE cliente IS NOT NULL AND cliente != '' ORDER BY cliente"
            cursor.execute(sql)
            return {"clientes": [r['cliente'] for r in cursor.fetchall()]}
    except Exception as e:
        return {"erro": str(e)}, 500
    finally:
        db.close()

# --- ROTA HORÁRIOS OCUPADOS (Para o Painel Operacional) ---
@app.get("/api/horarios-ocupados")
def get_horarios_ocupados(data: str):
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            # BUSCANDO NA COLUNA 'hora' (Padronizada)
            sql = "SELECT hora FROM db_pedido_pedidos WHERE data_emissao = %s"
            cursor.execute(sql, (data,))
            resultados = cursor.fetchall()
            return {"ocupados": [r['hora'] for r in resultados if r['hora']]}
    except Exception as e:
        return {"erro": str(e)}, 500
    finally:
        db.close()

# --- ROTA METRICAS ---
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
            
            cursor.execute("SELECT pedido_id, correlation_id, status, data_emissao FROM db_pedido_pedidos ORDER BY data_emissao DESC LIMIT 50")
            recentes = cursor.fetchall()
            for r in recentes:
                if r['data_emissao']: r['data_emissao'] = str(r['data_emissao'])
            
            return {
                "total_criados": criados,
                "total_confirmados": confirmados,
                "total_cancelados": cancelados,
                "pedidos_recentes": recentes
            }
    except Exception as e:
        return {"erro": str(e)}, 500
    finally:
        db.close()