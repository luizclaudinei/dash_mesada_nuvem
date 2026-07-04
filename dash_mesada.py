import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.express as px
import psycopg2
from psycopg2.extras import RealDictCursor

st.set_page_config(page_title="Dashboard - Mesada", layout="wide")

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Dashboard Mesada - Login Privado")
    senha = st.text_input("Insira a senha para acessar", type="password")
    
    if st.button("Entrar"):
        if senha == st.secrets.get("senha_app", ""):
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("❌ Senha incorreta!")
    st.stop()

@st.cache_resource
def conectar_neon():
    try:
        return psycopg2.connect(st.secrets["database_url"])
    except Exception as e:
        st.error(f"❌ Erro ao conectar ao Neon: {e}")
        st.stop()

conn = conectar_neon()

def criar_tabela():
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transacoes (
                    id SERIAL PRIMARY KEY,
                    data DATE NOT NULL,
                    descricao VARCHAR(255) NOT NULL,
                    categoria VARCHAR(100) NOT NULL,
                    valor NUMERIC(10, 2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
    except Exception as e:
        st.error(f"❌ Erro ao criar tabela: {e}")

criar_tabela()

def carregar_dados():
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT data, descricao, categoria, valor FROM transacoes ORDER BY data DESC;")
            registros = cur.fetchall()
        
        if registros:
            df = pd.DataFrame(registros)
            df["data"] = pd.to_datetime(df["data"])
            return df
        else:
            return pd.DataFrame(columns=["data", "descricao", "categoria", "valor"])
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        return pd.DataFrame(columns=["data", "descricao", "categoria", "valor"])

if "dados" not in st.session_state:
    st.session_state.dados = carregar_dados()

st.sidebar.title("➕ Adicionar Transação")

CATEGORIAS = ["Jardinagem", "Vestuário", "Alimentação", "Diversos", "Mesada", "Transporte", "Lazer", "Moradia", "Investimentos"]

with st.sidebar.form(key="form_transacoes", clear_on_submit=True):
    data = st.date_input("Data", value=datetime.today())
    descricao = st.text_input("Descrição")
    categoria = st.selectbox("Categoria", CATEGORIAS)
    valor = st.number_input("Valor (positivo = entrada, negativo = saída)", step=1)
    botao_enviar = st.form_submit_button("✅ Adicionar")

if botao_enviar:
    if not descricao:
        st.error("❌ Descrição é obrigatória!")
    elif valor == 0:
        st.error("❌ Valor não pode ser zero!")
    else:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO transacoes (data, descricao, categoria, valor) VALUES (%s, %s, %s, %s)",
                    (data, descricao, categoria, float(valor))
                )
                conn.commit()
            
            st.success("✅ Transação adicionada com sucesso!")
            st.session_state.dados = carregar_dados()
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erro ao adicionar transação: {e}")

df = carregar_dados()

if df.empty:
    st.info("📊 Adicione transações para começar.")
else:
    df_filtro = df.copy()
    df_filtro["data"] = pd.to_datetime(df_filtro["data"]).dt.normalize()
    df_filtro.sort_values("data", inplace=True)

    with st.sidebar.expander("🔍 Filtros", expanded=False):
        categorias_filtro = st.multiselect(
            "Categorias",
            options=sorted(df_filtro["categoria"].dropna().unique()),
            default=sorted(df_filtro["categoria"].dropna().unique())
        )

        inicio_periodo, final_periodo = st.date_input(
            "Período",
            value=(df_filtro["data"].min().date(), df_filtro["data"].max().date())
        )

    df_filtrado = df_filtro.loc[
        (df_filtro["categoria"].isin(categorias_filtro)) & 
        (df_filtro["data"].between(pd.to_datetime(inicio_periodo), pd.to_datetime(final_periodo)))
    ]

    st.title("💰 Dashboard - Mesada")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total = df_filtrado["valor"].sum()
        st.metric("💵 Saldo Total", f"R$ {total:,.2f}")

    with col2:
        entradas = df_filtrado[df_filtrado["valor"] > 0]["valor"].sum()
        st.metric("📈 Entradas", f"R$ {entradas:,.2f}")

    with col3:
        saidas = df_filtrado[df_filtrado["valor"] < 0]["valor"].sum()
        st.metric("📉 Saídas", f"R$ {saidas:,.2f}")

    with col4:
        transacoes = len(df_filtrado)
        st.metric("📋 Transações", transacoes)

    st.subheader("📈 Análises")

    col1, col2 = st.columns(2)

    with col1:
        if not df_filtrado.empty:
            gastos_categoria = df_filtrado.groupby("categoria")["valor"].sum().sort_values()
            fig_categoria = px.bar(
                x=gastos_categoria.values,
                y=gastos_categoria.index,
                orientation="h",
                title="Valor por Categoria",
                labels={"x": "Valor (R$)", "y": "Categoria"},
                color=gastos_categoria.values,
                color_continuous_scale="RdYlGn"
            )
            st.plotly_chart(fig_categoria, width='stretch')

    with col2:
        if not df_filtrado.empty:
            evolucao = df_filtrado.sort_values("data").groupby("data")["valor"].sum().cumsum()
            fig_evolucao = px.line(
                x=evolucao.index,
                y=evolucao.values,
                title="Evolução do Saldo",
                labels={"x": "Data", "y": "Saldo Acumulado (R$)"},
                markers=True
            )
            st.plotly_chart(fig_evolucao, width='stretch')

    st.subheader("📋 Transações")

    df_exibir = df_filtrado[["data", "descricao", "categoria", "valor"]].copy()
    df_exibir = df_exibir.sort_values("data", ascending=False)
    df_exibir.columns = ["Data", "Descrição", "Categoria", "Valor"]
    df_exibir["Valor"] = df_exibir["Valor"].apply(lambda x: f"R$ {x:,.2f}")

    st.dataframe(df_exibir, width='stretch', hide_index=True)

if st.sidebar.button("🚪 Sair"):
    st.session_state.autenticado = False
    st.session_state.dados = None
    st.rerun()