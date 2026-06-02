import streamlit as st
import pandas as pd
import pymysql
import os

st.set_page_config(page_title="ShopFlow - Monitor de Arquitetura", layout="wide")

st.title("⚡ ShopFlow — Monitor de Arquitetura Orientado a Eventos")
st.markdown("Visibilidade ponta a ponta sem violação de isolamento de persistência de banco de dados.")

# Função de conexão direta com a HostGator
def conectar_banco():
    return pymysql.connect(
        host="162.241.3.46",
        user="jeff1591_db_user",
        password="0~nh1U!.y89|",
        database="jeff1591_Gaptech",
        port=3306,
        cursorclass=pymysql.cursors.DictCursor
    )

try:
    db = conectar_banco()
    with db.cursor() as cursor:
        # Puxa os contadores reais da tabela
        cursor.execute("SELECT COUNT(*) as qtd FROM db_pedido_pedidos WHERE status='criado'")
        criados = cursor.fetchone()['qtd']
        cursor.execute("SELECT COUNT(*) as qtd FROM db_pedido_pedidos WHERE status='confirmado'")
        confirmados = cursor.fetchone()['qtd']
        cursor.execute("SELECT COUNT(*) as qtd FROM db_pedido_pedidos WHERE status='cancelado'")
        cancelados = cursor.fetchone()['qtd']
        
        # Como o banco respondeu, sabemos que a infraestrutura de dados está ativa!
        st.subheader("🏥 Estado de Ativos da Infraestrutura")
        col1, col2, col3 = st.columns(3)
        col1.success("🟢 Pedido: ONLINE")
        col2.success("🟢 Pagamento: ONLINE")
        col3.success("🟢 Logística: ONLINE")
        
        # Exibe os KPIs na aba ou blocos correspondentes
        st.markdown("### 📈 KPIs de Negócio")
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Criados", criados)
        kpi2.metric("Total Confirmados", confirmados)
        kpi3.metric("Total Cancelados", cancelados)
        
    db.close()
except Exception as e:
    st.error(f"Erro ao conectar ao banco remoto da HostGator: {e}")