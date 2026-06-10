# /app/main.py
import threading
import time
from fastapi import FastAPI
from consumer import iniciar_consumer, conectar_db

app = FastAPI()

@app.on_event("startup")
def startup():
    # Inicia o consumer como uma thread separada
    t = threading.Thread(target=iniciar_consumer, daemon=True)
    t.start()

@app.get("/health")
def health():
    return {"status": "ok", "servico": "pedido"}

@app.get("/metrics")
def metrics():
    db = conectar_db()
    if not db:
        return {"erro": "Conexão com banco falhou"}
    
    try:
        with db.cursor() as cursor:
            # Consultas de contagem
            cursor.execute("SELECT COUNT(*) as qtd FROM pedidos WHERE status='criado'")
            criados = cursor.fetchone()['qtd']
            
            cursor.execute("SELECT COUNT(*) as qtd FROM pedidos WHERE status='confirmado'")
            confirmados = cursor.fetchone()['qtd']
            
            cursor.execute("SELECT COUNT(*) as qtd FROM pedidos WHERE status='cancelado'")
            cancelados = cursor.fetchone()['qtd']
            
            # Busca os 50 mais recentes
            cursor.execute("SELECT * FROM pedidos ORDER BY criado_em DESC LIMIT 50")
            recentes = cursor.fetchall()
            
            # Tratamento para serialização JSON
            for r in recentes:
                if 'criado_em' in r and r['criado_em']:
                    r['criado_em'] = str(r['criado_em'])
            
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