import streamlit as st
import pandas as pd
import plotly.express as px
from database import SessionLocal
import models

st.set_page_config(page_title="Finanças Pro", layout="wide", page_icon="💰")

st.title("📊 Painel Financeiro Inteligente")

db = SessionLocal()
gastos = db.query(models.Gasto).all()
db.close()

if not gastos:
    st.info("Aguardando registros no Telegram...")
else:
    df = pd.DataFrame([
        {
            "Data": g.data_hora, 
            "Categoria": g.categoria, 
            "Valor": g.valor, 
            "Pagamento": g.forma_pagamento
        } for g in gastos
    ])

    # Métricas de Topo
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Geral", f"R$ {df['Valor'].sum():,.2f}")
    m2.metric("Média por Gasto", f"R$ {df['Valor'].mean():,.2f}")
    m3.metric("Qtd. Registros", len(df))

    st.divider()

    # Gráficos
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Gastos por Categoria")
        fig_pie = px.pie(df, values='Valor', names='Categoria', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.subheader("Forma de Pagamento")
        resumo_pagamento = df.groupby("Pagamento")["Valor"].sum().reset_index()
        fig_pag = px.bar(resumo_pagamento, x="Pagamento", y="Valor", color="Pagamento", text_auto='.2f')
        st.plotly_chart(fig_pag, use_container_width=True)

    st.divider()

    # Tabela detalhada com formatação de moeda (R$)
    st.subheader("📋 Histórico Detalhado")
    st.dataframe(
        df.sort_values("Data", ascending=False), 
        use_container_width=True,
        column_config={
            "Valor": st.column_config.NumberColumn(
                "Valor",
                format="R$ %.2f"
            )
        }
    )