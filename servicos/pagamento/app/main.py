import threading
from fastapi import FastAPI
import pymysql
import os
from consumer import iniciar_consumer, conectar_db

app = FastAPI()

@app.on_event("startup")
def startup():
    # Inicializa o loop infinito do broker em thread dedicada
    t = threading.Thread(target=iniciar_consumer, daemon=True)
    t.start()

@app.get("/health")
def health():
    return {"status": "ok", "servico": "pedido"}

@app.get("/metrics")
def metrics():
    # Coleta de métricas diretas exigida para comunicação limpa isolada por serviço
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as qtd FROM pedidos WHERE status='criado'")
            criados = cursor.fetchone()['qtd']
            cursor.execute("SELECT COUNT(*) as qtd FROM pedidos WHERE status='confirmado'")
            confirmados = cursor.fetchone()['qtd']
            cursor.execute("SELECT COUNT(*) as qtd FROM pedidos WHERE status='cancelado'")
            cancelados = cursor.fetchone()['qtd']
            
            cursor.execute("SELECT * FROM pedidos ORDER BY criado_em DESC LIMIT 50")
            recentes = cursor.fetchall()
            
            # Formatação para string segura JSON serializável
            for r in recentes:
                if r['criado_em']:
                    r['criado_em'] = r['criado_em'].isoformat()
            
            return {
                "total_criados": criados,
                "total_confirmados": confirmados,
                "total_cancelados": cancelados,
                "total_entregues": confirmados, # Simulado baseado nas confirmações de fluxo direto
                "pedidos_recentes": recentes
            }
    except Exception as e:
        return {"erro": str(e)}
    finally:
        db.close()