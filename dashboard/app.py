import streamlit as st
import pandas as pd
import pymysql
import os

# Configuração global da página
st.set_page_config(page_title="MetalSync - Dashboard Express", layout="wide", initial_sidebar_state="expanded")

st.title("📊 MetalSync — Dashboard Express")
st.markdown("Monitoramento de Infraestrutura e KPIs de Negócio em Tempo Real.")
st.markdown("---")

# Função para conectar direto ao banco da HostGator (onde as cargas estão salvas)
def conectar_db():
    return pymysql.connect(
        host="162.241.3.46",
        user="jeff1591_db_user",
        password="0~nh1U!.y89|",
        database="jeff1591_Gaptech",
        port=3306,
        cursorclass=pymysql.cursors.DictCursor
    )

# Busca os dados reais diretamente do MySQL remoto
try:
    db = conectar_db()
    with db.cursor() as cursor:
        # Puxa os dados brutos da tabela para a aba de comunicação ao vivo
        cursor.execute("SELECT pedido_id, correlation_id, status, data_emissao FROM db_pedido_pedidos ORDER BY data_emissao DESC LIMIT 100")
        dados_pedidos = cursor.fetchall()
        
        # Puxa as métricas agregadas para os KPIs
        cursor.execute("SELECT COUNT(*) as total FROM db_pedido_pedidos")
        total_criados = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as total FROM db_pedido_pedidos WHERE status = 'confirmado'")
        total_confirmados = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as total FROM db_pedido_pedidos WHERE status = 'cancelado'")
        total_cancelados = cursor.fetchone()["total"]
        
    db.close()
    banco_online = True
except Exception as e:
    dados_pedidos = []
    total_criados = total_confirmados = total_cancelados = 0
    banco_online = False

# Criação das 3 abas exigidas pelo Módulo 4
aba_saude, aba_comunicacao, aba_kpis = st.tabs([
    "🏥 1. Saúde dos Ativos", 
    "🕒 2. Comunicação ao Vivo", 
    "📈 3. KPIs de Negócio"
])

# ==========================================
# ABA 1: SAÚDE DOS ATIVOS
# ==========================================
with aba_saude:
    st.subheader("Estado de Conectividade da Infraestrutura")
    st.write("Verificação de integridade baseada na persistência e comunicação com a malha de dados.")
    
    col1, col2, col3 = st.columns(3)
    
    if banco_online:
        col1.success("🟢 Gateway de Pedidos: ONLINE")
        col2.success("🟢 Orquestrador Saga: ONLINE")
        col3.success("🟢 Banco HostGator: CONECTADO")
    else:
        col1.error("🔴 Gateway de Pedidos: OFFLINE")
        col2.error("🔴 Orquestrador Saga: OFFLINE")
        col3.error("🔴 Banco HostGator: INDISPONÍVEL")

# ==========================================
# ABA 2: COMUNICAÇÃO AO VIVO
# ==========================================
with aba_comunicacao:
    st.subheader("Fluxo de Mensageria e Eventos Recentes")
    st.write("Lista contendo as últimas transações capturadas em tempo real.")
    
    if dados_pedidos:
        df = pd.DataFrame(dados_pedidos)
        df = df.astype(str)
        
        # Renomeia as colunas de forma amigável e corporativa
        df.columns = ["ID do Pedido", "Correlation ID", "Status da Saga", "Data/Hora Emissão"]
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Aguardando novas mensagens trafegarem pelas filas ou erro de conexão.")

# ==========================================
# ABA 3: KPIS DE NEGÓCIO
# ==========================================
with aba_kpis:
    st.subheader("Métricas de Desempenho e Tomada de Decisão")
    
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Pedidos Totais Recebidos", total_criados)
    kpi2.metric("Sagas Confirmadas", total_confirmados)
    kpi3.metric("Sagas Canceladas", total_cancelados)
    
    st.markdown("---")
    st.markdown("#### 🎯 Taxas de Conversão Exigidas")
    
    if total_criados > 0:
        taxa_aprovacao = (total_confirmados / total_criados) * 100
        taxa_bloqueio = (total_cancelados / total_criados) * 100
    else:
        taxa_aprovacao = 0.0
        taxa_bloqueio = 0.0
        
    col_taxa1, col_taxa2 = st.columns(2)
    col_taxa1.metric("📈 Taxa de Aprovação de Pagamentos", f"{taxa_aprovacao:.1f}%")
    col_taxa2.metric("🛡️ Taxa de Bloqueio Antifraude / Falhas", f"{taxa_bloqueio:.1f}%")