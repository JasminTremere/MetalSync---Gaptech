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

@app.post("/api/novo-pedido")
def criar_pedido(payload: dict):
    # TRUQUE DE DEBUG: Isso vai imprimir no terminal do servidor o que chegou do HTML
    print("===== DADOS QUE CHEGARAM DO FRONTEND =====")
    print(payload)
    print("==========================================")

    db = conectar_db()
    try:
        with db.cursor() as cursor:
            # Usando a sua nova coluna 'hora' em vez de 'horario'
            sql_pedido = """
                INSERT INTO db_pedido_pedidos 
                (pedido_id, cliente_id, data_emissao, valor_total, status, correlation_id, tipo_vale, itens_json, cliente, hora, prioridade) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql_pedido, (
                payload.get('pedido_id'),               
                payload.get('pedido_id'),               
                payload.get('data'),                    
                payload.get('total'),                   
                'criado',                               
                payload.get('pedido_id'),               
                'pecas',                                
                payload.get('itens_json'),              
                payload.get('cliente'),                 
                payload.get('horario'), # <<< A string "08:00 às 10:00" vai ser salva na nova coluna 'hora'
                payload.get('prioridade')               
            ))
            db.commit()
            return {"status": "sucesso"}
    except Exception as e:
        db.rollback()
        # Se falhar, o erro vermelho vai aparecer no terminal para você ler
        print(f"Erro no INSERT: {e}") 
        return {"status": "erro", "msg": str(e)}, 500

        
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
                if r['data_emissao']:
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

@app.get("/api/horarios-ocupados")
def get_horarios_ocupados(data: str):
    db = conectar_db()
    try:
        with db.cursor() as cursor:
            # Como agora o horário é inserido como texto, ele vai retornar um array com as strings dos horários ocupados.
            sql = "SELECT horario FROM db_pedido_pedidos WHERE data_emissao = %s"
            cursor.execute(sql, (data,))
            resultados = cursor.fetchall()
            
            lista_ocupados = [r['horario'] for r in resultados]
            return {"ocupados": lista_ocupados}
    finally:
        db.close()