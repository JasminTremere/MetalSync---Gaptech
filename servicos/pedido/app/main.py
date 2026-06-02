import threading
from fastapi import FastAPI
import os
import pymysql
from consumer import iniciar_consumer, conectar_db

app = FastAPI(title="MetalSync - Serviço de Pedidos")

@app.on_event("startup")
def startup():
    t = threading.Thread(target=iniciar_consumer, daemon=True)
    t.start()

@app.get("/health")
def health():
    return {"status": "ok", "servico": "pedido"}

# ROTA DO POST CORRIGIDA PARA O SEU BANCO REAL
@app.post("/pedidos")
def criar_pedido(payload: dict):
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            correlation_id = payload.get("correlation_id")
            inner_payload = payload.get("payload", {})
            pedido_id = inner_payload.get("pedido_id")
            valor_total = inner_payload.get("valor_total", 0.0)

            # AJUSTE AQUI: Nome real da sua tabela mapeada no phpMyAdmin
            sql = """
                INSERT INTO db_pedido_pedidos (pedido_id, correlation_id, status, pagamento_ok, fraude_ok, data_emissao)
                VALUES (%s, %s, 'criado', NULL, NULL, NOW())
            """
            cursor.execute(sql, (pedido_id, correlation_id))
            db.commit()
            
            print(f" [📝 API Pedidos] Estado salvo no banco. Pedido: {pedido_id[:6]}... | Saga Iniciada.")
            return {"status": "pedido.criado", "pedido_id": pedido_id, "correlation_id": correlation_id}
            
    except Exception as e:
        print(f" [x] Erro ao registrar pedido na API: {e}")
        db.rollback()
        return {"status": "erro", "detalhes": str(e)}, 500
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