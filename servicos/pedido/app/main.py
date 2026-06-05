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

@app.get("/health")
def health():
    return {"status": "ok", "servico": "pedido"}

@import requests # Certifique-se de que está importado no topo

@app.post("/api/novo-pedido")
def criar_pedido(payload: dict):
    db = conectar_db()
    try:
        # 1. Inserção no Banco
        with db.cursor() as cursor:
            sql = "INSERT INTO db_pedido_pedidos (pedido_id, cliente, data_emissao, horario, prioridade, valor_total, itens_json) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (
                payload.get('pedido_id'), payload.get('cliente'), payload.get('data'),
                payload.get('horario'), payload.get('prioridade'), payload.get('total'),
                payload.get('itens_json')
            ))
            db.commit()
            print("Sucesso: Salvo no MySQL")
    except Exception as e:
        print(f"Erro banco: {e}")
        return {"status": "erro", "msg": str(e)}, 500
    finally:
        db.close()

    # 2. Disparo para o n8n (FORA do bloco do banco para não travar)
    try:
        # Tente usar o IP da máquina real se estiver no Docker, ou localhost se rodar local
        # O timeout curto é para não travar a tela caso o n8n não responda
        requests.post("http://localhost:5678/webhook/pedido", json=payload, timeout=3)
        print("Sucesso: Enviado ao n8n")
    except Exception as e:
        print(f"Aviso: N8N não respondeu: {e}")

    return {"status": "ok"}
    
     
# --- 2. ROTA LISTAR PEDIDOS ---
@app.get("/api/pedidos")
def listar_pedidos():
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            # Corrigido para 'horario'
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
        return {"erro": str(e)}, 500
    finally:
        db.close()

# --- 3. ROTA LISTAR CLIENTES ---
@app.get("/api/clientes")
def listar_clientes():
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            sql = "SELECT DISTINCT cliente FROM db_pedido_pedidos WHERE cliente IS NOT NULL AND cliente != '' ORDER BY cliente;"
            cursor.execute(sql)
            return {"clientes": [r['cliente'] for r in cursor.fetchall()]}
    except Exception as e:
        return {"erro": str(e)}, 500
    finally:
        db.close()

@app.get("/api/horarios-ocupados")
def get_horarios_ocupados(data: str):
    # ... (código do banco) ...
    resultados = cursor.fetchall()
    # Certifique-se de que o nome aqui é exatamente o que o JS espera
    return {"pedidos": resultados}
    finally:
        db.close()

# Rota para mover pedido (trocar horário ou atualizar)
@app.post("/api/mover-pedido")
def mover_pedido(payload: dict):
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            # Atualiza o horário do pedido específico
            sql = "UPDATE db_pedido_pedidos SET horario = %s WHERE pedido_id = %s"
            cursor.execute(sql, (payload.get('novo_horario'), payload.get('pedido_id')))
            db.commit()
            return {"status": "sucesso"}
    except Exception as e:
        db.rollback()
        return {"erro": str(e)}, 500
    finally:
        db.close()
        
# --- ADICIONE ESTA NOVA ROTA LOGO ABAIXO ---
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
        return {"erro": str(e)}, 500
    finally:
        db.close()

# --- 5. ROTA METRICAS ---
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