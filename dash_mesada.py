import streamlit as st
from datetime import datetime
import os
import pandas as pd
import plotly.express as px

st.set_page_config(page_title = "Dashboard - Mesada", layout="wide")

caminho_transacoes = "transacoesmesada.csv"

if "dados" not in st.session_state:
        
        if os.path.exists(caminho_transacoes):
                st.session_state.dados = pd.read_csv (caminho_transacoes, parse_dates=["Data"])
                #converter coluna Valor para numérico
                st.session_state.dados["Valor"] = pd.to_numeric(st.session_state.dados["Valor"], errors='coerce')
        else:
                st.session_state.dados = pd.DataFrame(columns= ["Data", "Descrição", "Categoria", "Valor"])

st.sidebar.title("Adicionar Transação")

CATEGORIAS = ["Jardinagem", "Vestuário", "Alimentação", "Diversos", "Mesada", "Transporte", "Lazer", "Moradia", "Investimentos"]

with st.sidebar.form(key = "form_transacoes", clear_on_submit=True):

        data = st.date_input("Data", value=datetime.today())
        descricao = st.text_input("Descrição")
        categoria = st.selectbox("Categoria", CATEGORIAS)
        valor = st.number_input("Valor (positivo = entrada, negativo = saída)",
                                step=1)
        botao_enviar = st.form_submit_button("Adicionar")


if botao_enviar:
        
        st.session_state.dados = pd.concat(
            [
                st.session_state.dados,
                pd.DataFrame({

                        "Data": [pd.to_datetime(data)],
                        "Descrição": [descricao],
                        "Categoria": [categoria],
                        "Valor": [valor]

                })   
            ], ignore_index=True
        )
        st.success("Transação adicionada!")
        st.session_state.dados.to_csv(caminho_transacoes, index = False)

if st.session_state.dados.empty:
        st.info("Adicione transações para começar.")

df = st.session_state.dados.copy()
df["Data"] = pd.to_datetime(df["Data"]).dt.normalize()
df.sort_values("Data", inplace=True)

with st.sidebar.expander("filtros", expanded=False):

        categorias_filtro = st.multiselect("Categorias",
                                   options=sorted(df["Categoria"].dropna().unique()),
                                   default=sorted(df["Categoria"].dropna().unique()))

# Verificar se há dados antes de definir período
        if not df.empty:
                inicio_periodo, final_periodo = st.date_input("Período",
                                        value=(df["Data"].min().date(),
                                                df["Data"].max().date()))
        else:
                # Valores padrão quando não há dados
                hoje = datetime.today().date()
                inicio_periodo, final_periodo = st.date_input("Período",
                                        value=(hoje, hoje))


df_filtrado = df.loc[(df["Categoria"].isin(categorias_filtro)) & (df["Data"].between(pd.to_datetime(inicio_periodo), pd.to_datetime(final_periodo)))]


entradas = df_filtrado.loc[df_filtrado["Valor"] > 0, "Valor"].sum()
saidas = df_filtrado.loc[df_filtrado["Valor"] < 0, "Valor"].sum()
saldo = entradas + saidas

metrica1, metrica2, metrica3 = st.columns(3)
metrica1.metric("Entradas", f"R$ {entradas:,.2f}")
metrica2.metric("Saídas", f"R$ {saidas:,.2f}")
metrica3.metric("Saldo", f"R$ {saldo:,.2f}")

st.markdown("## Transações")

st.dataframe(
        df_filtrado.style.format({"Data": "{:%Y-%m-%d}"}),
        use_container_width=True,
        hide_index=True
)

with st.expander("Editar ou excluir transações"):

        edicao_df = st.data_editor(
                st.session_state.dados,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True               
        )

        if st.button("Salvar alterações"):
                edicao_df = edicao_df.dropna()
                st.session_state.dados = edicao_df
                st.session_state.dados.to_csv(caminho_transacoes, index = False)
                st.rerun()

        

if df_filtrado.empty:
        st.warning("Sem dados no intervalo selecionado")

else:
        
        linha_grafico = df_filtrado.groupby("Data").sum().cumsum().reset_index()
        grafico_saldo = px.line(linha_grafico, x = "Data", y = "Valor", title="Evolução de Saldo Diário")
        grafico_saldo.update_xaxes(tickformat = "%d %b %Y")
        st.plotly_chart(grafico_saldo, use_container_width=True)


if not df_filtrado.empty:

        tabela_com_gastos = df_filtrado[df_filtrado["Valor"] < 0]
        
        dados_pizza = tabela_com_gastos.groupby("Categoria") ["Valor"].sum().abs().reset_index()
        dados_barras = tabela_com_gastos.nsmallest(5, "Valor").copy()
        dados_barras["Valor"]= dados_barras["Valor"].abs()

        grafico_pizza = px.pie(dados_pizza, names="Categoria", values="Valor", title="Distribuição de Despesas")
        st.plotly_chart(grafico_pizza, use_container_width=True)

        grafico_barras = px.bar(dados_barras, x = "Descrição", y = "Valor", title="Top 5 Despesas", text_auto=True)
        st.plotly_chart(grafico_barras, use_container_width=True)


csv_operacoes = df_filtrado.to_csv(index=False).encode("utf-8")
st.download_button("Baixar CSV Filtrado", csv_operacoes, "mesada_filtro.csv", "text/csv")