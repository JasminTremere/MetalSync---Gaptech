import streamlit as st
import requests
import pandas as pd
import os

# Configuração global da página
st.set_page_config(page_title="MetalSync - Dashboard Express", layout="wide", initial_sidebar_state="expanded")

st.title("📊 MetalSync — Dashboard Express (Módulo 4)")
st.markdown("Monitoramento de Infraestrutura e KPIs de Negócio em Tempo Real.")
st.markdown("---")

# Configuração de URLs (Lendo a rede interna do Docker)
API_METRICS_URL = os.getenv("API_METRICS_URL", "http://pedido:8001/metrics")
HEALTH_PEDIDOD_URL = "http://pedido:8001/health"
HEALTH_PAGAMENTO_URL = "http://pagamento:8002/health"
HEALTH_LOGISTICA_URL = "http://logistica:8003/health"

# Coleta de dados da API de Métricas
try:
    response = requests.get(API_METRICS_URL, timeout=3)
    if response.status_code == 200:
        metrics_data = response.json()
    else:
        metrics_data = {}
except Exception:
    metrics_data = {}

# Definição das 3 abas obrigatórias do Módulo 4
aba_saude, aba_comunicacao, aba_kpis = st.tabs([
    "🏥 1. Saúde dos Ativos", 
    "🕒 2. Comunicação ao Vivo", 
    "📈 3. KPIs de Negócio"
])

# ==========================================
# ABA 1: SAÚDE DOS ATIVOS
# ==========================================
with aba_saude:
    st.subheader("Estado de Conectividade dos Microsserviços")
    st.write("Verificação de integridade via requisições HTTP nos endpoints `/health` de cada contêiner.")
    
    col1, col2, col3 = st.columns(3)
    
    # Checagem do Microsserviço de Pedidos
    try:
        r = requests.get(HEALTH_PEDIDOD_URL, timeout=2)
        if r.status_code == 200:
            col1.success("🟢 Serviço Pedidos: ONLINE")
        else:
            col1.error("🔴 Serviço Pedidos: ERRO HTTP")
    except Exception:
        col1.error("🔴 Serviço Pedidos: OFFLINE")

    # Checagem do Microsserviço de Pagamentos
    try:
        r = requests.get(HEALTH_PAGAMENTO_URL, timeout=2)
        if r.status_code == 200:
            col2.success("🟢 Serviço Pagamentos: ONLINE")
        else:
            col2.error("🔴 Serviço Pagamentos: ERRO HTTP")
    except Exception:
        col2.error("🔴 Serviço Pagamentos: OFFLINE")

    # Checagem do Microsserviço de Logística
    try:
        r = requests.get(HEALTH_LOGISTICA_URL, timeout=2)
        if r.status_code == 200:
            col3.success("🟢 Serviço Logística: ONLINE")
        else:
            col3.error("🔴 Serviço Logística: ERRO HTTP")
    except Exception:
        col3.error("🔴 Serviço Logística: OFFLINE")

# ==========================================
# ABA 2: COMUNICAÇÃO AO VIVO (CORRIGIDA)
# ==========================================
with aba_comunicacao:
    st.subheader("Fluxo de Mensageria e Eventos Recentes")
    st.write("Lista contendo as últimas transações capturadas do banco de dados MySQL na HostGator.")
    
    pedidos_recentes = metrics_data.get("pedidos_recentes", [])
    
    if pedidos_recentes:
        # Cria o DataFrame bruto com o que veio da API
        df = pd.DataFrame(pedidos_recentes)
        
        # Força a conversão de todas as colunas para string para evitar quebras de exibição
        df = df.astype(str)
        
        # Exibe a tabela bruta ocupando a largura total da tela de forma responsiva
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Aguardando novas mensagens trafegarem pelas filas do RabbitMQ...")

# ==========================================
# ABA 3: KPIS DE NEGÓCIO
# ==========================================
with aba_kpis:
    st.subheader("Métricas de Desempenho e Tomada de Decisão")
    
    total_criados = metrics_data.get("total_criados", 0)
    total_confirmados = metrics_data.get("total_confirmados", 0)
    total_cancelados = metrics_data.get("total_cancelados", 0)
    
    # Exibição dos cards numéricos principais
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Pedidos Totais Recebidos", total_criados)
    kpi2.metric("Sagas Confirmadas", total_confirmados)
    kpi3.metric("Sagas Canceladas", total_cancelados)
    
    st.markdown("---")
    st.markdown("#### 🎯 Taxas de Conversão Exigidas")
    
    # Cálculo das taxas percentuais com tratamento para divisão por zero
    if total_criados > 0:
        taxa_aprovacao = (total_confirmados / total_criados) * 100
        taxa_bloqueio = (total_cancelados / total_criados) * 100
    else:
        taxa_aprovacao = 0.0
        taxa_bloqueio = 0.0
        
    col_taxa1, col_taxa2 = st.columns(2)
    col_taxa1.metric("📈 Taxa de Aprovação de Pagamentos", f"{taxa_aprovacao:.1f}%")
    col_taxa2.metric("🛡️ Taxa de Bloqueio Antifraude / Falhas", f"{taxa_bloqueio:.1f}%")