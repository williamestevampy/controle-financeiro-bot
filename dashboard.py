import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import SessionLocal
import models
from datetime import datetime
import calendar
import io
from fpdf import FPDF
from fpdf.enums import XPos, YPos

_NL = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


def fmt_br(valor, decimais=2):
    """Formata float para o padrão brasileiro: 1.520,60"""
    s = f"{valor:,.{decimais}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


st.set_page_config(
    page_title="Finanças Pro",
    layout="wide",
    page_icon="💰",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 1rem; }
    #MainMenu, footer, header { visibility: hidden; }

    .kpi-card {
        background: #1C1F2E;
        border-radius: 14px;
        padding: 1.1rem 1.4rem;
        border-left: 4px solid #4B9FFF;
        margin-bottom: 0.6rem;
    }
    .kpi-card.green  { border-color: #00D4AA; }
    .kpi-card.red    { border-color: #FF4B6E; }
    .kpi-card.blue   { border-color: #4B9FFF; }
    .kpi-card.yellow { border-color: #FFD93D; }

    .kpi-label {
        font-size: 0.72rem;
        color: #8B8FA8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.2rem;
    }
    .kpi-value {
        font-size: 1.55rem;
        font-weight: 700;
        color: #FAFAFA;
        line-height: 1.2;
    }
    .positive { color: #00D4AA; }
    .negative { color: #FF4B6E; }

    .section-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #8B8FA8;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin: 1.2rem 0 0.6rem;
        border-bottom: 1px solid #2A2D3E;
        padding-bottom: 0.3rem;
    }

    .provento-row {
        background: #1C1F2E;
        border-radius: 10px;
        padding: 0.65rem 1rem;
        margin-bottom: 0.4rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .provento-desc { color: #FAFAFA; font-size: 0.95rem; }
    .provento-dia  { color: #8B8FA8; font-size: 0.78rem; margin-left: 0.3rem; }
    .provento-val  { color: #00D4AA; font-weight: 700; font-size: 1rem; white-space: nowrap; }

    .analise-card {
        background: #1C1F2E;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.5rem;
        border-top: 3px solid;
    }
    .analise-card.ok     { border-color: #00D4AA; }
    .analise-card.warn   { border-color: #FFD93D; }
    .analise-card.danger { border-color: #FF4B6E; }

    .rec-item {
        background: #1C1F2E;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.35rem;
        font-size: 0.9rem;
        color: #FAFAFA;
        border-left: 3px solid #4B9FFF;
    }

    @media (max-width: 768px) {
        .kpi-value { font-size: 1.1rem; }
        .block-container { padding-left: 0.5rem; padding-right: 0.5rem; }
    }
</style>
""", unsafe_allow_html=True)

# ── MESES EM PORTUGUÊS ────────────────────────────────────────────────────────
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}
MESES_PT_ACENTUADO = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

# ── GERAÇÃO DE PDF ────────────────────────────────────────────────────────────
def gerar_pdf(mes_nome, ano, df_g, df_p, total_receitas, total_gastos, saldo, linhas_analise):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Cabeçalho
    pdf.set_fill_color(28, 31, 46)
    pdf.rect(0, 0, 210, 30, "F")
    pdf.set_text_color(250, 250, 250)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_y(8)
    pdf.cell(0, 10, f"Relatorio Financeiro - {mes_nome} {ano}", align="C", **_NL)
    pdf.set_y(35)
    pdf.set_text_color(30, 30, 30)

    # Resumo KPI
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(240, 240, 245)
    pdf.cell(0, 8, "Resumo do Mes", **_NL, fill=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(1)
    pdf.cell(60, 7, "Receitas:")
    pdf.set_text_color(0, 140, 100)
    pdf.cell(0, 7, f"R$ {fmt_br(total_receitas)}", **_NL)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(60, 7, "Gastos:")
    pdf.set_text_color(200, 40, 60)
    pdf.cell(0, 7, f"R$ {fmt_br(total_gastos)}", **_NL)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(60, 7, "Saldo:")
    cor = (0, 140, 100) if saldo >= 0 else (200, 40, 60)
    pdf.set_text_color(*cor)
    sinal = "+" if saldo >= 0 else ""
    pdf.cell(0, 7, f"{sinal}R$ {fmt_br(saldo)}", **_NL)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(4)

    # Proventos
    if not df_p.empty:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(240, 240, 245)
        pdf.cell(0, 8, "Receitas do Mes", **_NL, fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.ln(1)
        for _, row in df_p.iterrows():
            if pd.notna(row["Dia"]) and row["Dia"]:
                dia_txt = f"dia {int(row['Dia'])}"
            else:
                dia_txt = row["Data"].strftime("%d/%m")
            desc = str(row["Descricao"])[:40]
            pdf.cell(100, 6, f"  {desc} ({dia_txt})")
            pdf.cell(0, 6, f"R$ {fmt_br(row['Valor'])}", **_NL)
        pdf.ln(3)

    # Gastos por categoria
    if not df_g.empty:
        cats = df_g.groupby("Categoria")["Valor"].sum().sort_values(ascending=False)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(240, 240, 245)
        pdf.cell(0, 8, "Gastos por Categoria", **_NL, fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.ln(1)
        for cat, val in cats.items():
            pct = val / total_gastos * 100 if total_gastos > 0 else 0
            pdf.cell(100, 6, f"  {str(cat)[:40]}")
            pdf.cell(40, 6, f"R$ {fmt_br(val)}")
            pdf.cell(0, 6, f"({pct:.0f}%)", **_NL)
        pdf.ln(3)

    # Análise de economia
    if linhas_analise:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(240, 240, 245)
        pdf.cell(0, 8, "Analise de Economia", **_NL, fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.ln(1)
        for linha in linhas_analise:
            linha_safe = linha.encode("latin-1", errors="replace").decode("latin-1")
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 6, f"  {linha_safe}")
        pdf.ln(3)

    # Histórico detalhado
    if not df_g.empty:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(240, 240, 245)
        pdf.cell(0, 8, "Historico de Gastos (ultimos 50)", **_NL, fill=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.ln(1)
        for _, row in df_g.sort_values("Data", ascending=False).head(50).iterrows():
            data_str = row["Data"].strftime("%d/%m")
            cat = str(row["Categoria"])[:25]
            pag = str(row["Pagamento"])[:12]
            linha = f"  {data_str}  {cat:<25}  R$ {row['Valor']:>8.2f}  {pag}"
            linha_safe = linha.encode("latin-1", errors="replace").decode("latin-1")
            pdf.set_x(pdf.l_margin)
            pdf.cell(pdf.epw, 5, linha_safe, **_NL)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💰 Finanças Pro")
    st.markdown("---")

    hoje = datetime.now()
    opcoes = []
    for i in range(12):
        mes = hoje.month - i
        ano = hoje.year
        while mes <= 0:
            mes += 12
            ano -= 1
        opcoes.append((f"{MESES_PT_ACENTUADO[mes]} {ano}", mes, ano))

    labels = [o[0] for o in opcoes]
    idx = st.selectbox("📅 Mês de Referência", range(len(labels)), format_func=lambda i: labels[i])
    mes_sel, ano_sel = opcoes[idx][1], opcoes[idx][2]

    st.markdown("---")
    mostrar_historico = st.checkbox("📈 Tendência histórica", value=False)

    st.markdown("---")
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    with st.expander("➕ Registrar Receita"):
        desc_rec  = st.text_input("Descrição", value="Salário", key="rec_desc")
        valor_rec = st.number_input("Valor (R$)", min_value=0.01, step=100.0, value=1500.0, key="rec_valor")
        dia_rec   = st.selectbox("Dia do mês", [15, 30, 1, 5, 10, 20, 25], key="rec_dia")
        if st.button("💾 Salvar Receita", use_container_width=True, key="btn_rec"):
            _db = SessionLocal()
            _db.add(models.Provento(descricao=desc_rec, valor=float(valor_rec), dia=int(dia_rec)))
            _db.commit()
            _db.close()
            st.success(f"Receita salva: R$ {fmt_br(valor_rec)}")
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")
    st.caption("Use o bot no Telegram para registrar gastos e salários.")

# ── FUNÇÕES DE EXCLUSÃO ───────────────────────────────────────────────────────
def deletar_gasto(gasto_id: int):
    db = SessionLocal()
    try:
        obj = db.query(models.Gasto).filter(models.Gasto.id == gasto_id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False
    finally:
        db.close()

def deletar_provento(provento_id: int):
    db = SessionLocal()
    try:
        obj = db.query(models.Provento).filter(models.Provento.id == provento_id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False
    finally:
        db.close()

# ── CARGA DE DADOS ────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        db = SessionLocal()
        gastos = db.query(models.Gasto).all()
        proventos = db.query(models.Provento).all()
        db.close()
        return gastos, proventos, None
    except Exception as e:
        return [], [], str(e)

gastos_raw, proventos_raw, erro = carregar_dados()

# ── CABEÇALHO ─────────────────────────────────────────────────────────────────
st.markdown("# 📊 Painel Financeiro")
st.markdown(f"**{MESES_PT_ACENTUADO[mes_sel]} {ano_sel}**")

if erro:
    st.error("⚠️ Erro de conexão com o banco de dados")
    with st.expander("Detalhes técnicos"):
        st.code(erro)
    st.stop()

# ── DATAFRAMES ────────────────────────────────────────────────────────────────
if gastos_raw:
    df_gastos = pd.DataFrame([{
        "id": g.id,
        "Data": g.data_hora,
        "Categoria": g.categoria,
        "Valor": g.valor,
        "Pagamento": g.forma_pagamento,
    } for g in gastos_raw])
    df_gastos["Mes"] = df_gastos["Data"].dt.month
    df_gastos["Ano"] = df_gastos["Data"].dt.year
    df_gastos["Dia"] = df_gastos["Data"].dt.day
else:
    df_gastos = pd.DataFrame(columns=["Data", "Categoria", "Valor", "Pagamento", "Mes", "Ano", "Dia"])

if proventos_raw:
    df_proventos = pd.DataFrame([{
        "id": p.id,
        "Data": p.data_hora,
        "Descricao": p.descricao,
        "Valor": p.valor,
        "Dia": p.dia,
    } for p in proventos_raw])
    df_proventos["Mes"] = df_proventos["Data"].dt.month
    df_proventos["Ano"] = df_proventos["Data"].dt.year
else:
    df_proventos = pd.DataFrame(columns=["Data", "Descricao", "Valor", "Dia", "Mes", "Ano"])

# Filtro por mês selecionado
df_g = df_gastos[(df_gastos["Mes"] == mes_sel) & (df_gastos["Ano"] == ano_sel)].copy()
df_p = df_proventos[(df_proventos["Mes"] == mes_sel) & (df_proventos["Ano"] == ano_sel)].copy()

# ── KPI CARDS ─────────────────────────────────────────────────────────────────
total_receitas = df_p["Valor"].sum() if not df_p.empty else 0.0
total_gastos_v = df_g["Valor"].sum() if not df_g.empty else 0.0
saldo = total_receitas - total_gastos_v
n_trans = len(df_g)

saldo_class = "positive" if saldo >= 0 else "negative"
saldo_sinal = "+" if saldo >= 0 else ""

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""<div class="kpi-card green">
        <div class="kpi-label">Receitas</div>
        <div class="kpi-value">R$ {fmt_br(total_receitas)}</div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class="kpi-card red">
        <div class="kpi-label">Gastos</div>
        <div class="kpi-value">R$ {fmt_br(total_gastos_v)}</div>
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class="kpi-card blue">
        <div class="kpi-label">Saldo</div>
        <div class="kpi-value"><span class="{saldo_class}">{saldo_sinal}R$ {fmt_br(saldo)}</span></div>
    </div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""<div class="kpi-card yellow">
        <div class="kpi-label">Transações</div>
        <div class="kpi-value">{n_trans}</div>
    </div>""", unsafe_allow_html=True)

# ── ANÁLISE SINTÉTICA DE ECONOMIA ────────────────────────────────────────────
st.markdown('<div class="section-title">💡 Análise Inteligente de Economia</div>', unsafe_allow_html=True)

# Divide proventos por dia de entrada (15 vs 30)
sal_15 = float(df_p[df_p["Dia"] == 15]["Valor"].sum()) if not df_p.empty else 0.0
sal_30 = float(df_p[(df_p["Dia"] >= 28) | (df_p["Dia"] == 30)]["Valor"].sum()) if not df_p.empty else 0.0
if sal_15 == 0 and sal_30 == 0 and total_receitas > 0:
    sal_15 = sal_30 = total_receitas / 2

# Gastos por período
gastos_p1 = float(df_g[df_g["Dia"] <= 15]["Valor"].sum()) if not df_g.empty else 0.0
gastos_p2 = float(df_g[df_g["Dia"] > 15]["Valor"].sum()) if not df_g.empty else 0.0
saldo_p1 = sal_15 - gastos_p1
saldo_p2 = sal_30 - gastos_p2

# Cards dos dois períodos
pa1, pa2 = st.columns(2)
with pa1:
    cls = "ok" if saldo_p1 >= 0 else "danger"
    sinal_p1 = "+" if saldo_p1 >= 0 else ""
    st.markdown(f"""<div class="analise-card {cls}">
        <div class="kpi-label">Período 1 — Dias 1 a 15</div>
        <div style="margin-top:0.4rem; font-size:0.85rem; color:#8B8FA8;">
            Salário dia 15: <b style="color:#00D4AA">R$ {fmt_br(sal_15)}</b><br>
            Gastos 1–15: <b style="color:#FF4B6E">R$ {fmt_br(gastos_p1)}</b>
        </div>
        <div style="margin-top:0.5rem; font-size:1.2rem; font-weight:700;
            color:{'#00D4AA' if saldo_p1 >= 0 else '#FF4B6E'}">
            Saldo: {sinal_p1}R$ {fmt_br(saldo_p1)}
        </div>
    </div>""", unsafe_allow_html=True)

with pa2:
    cls = "ok" if saldo_p2 >= 0 else "danger"
    sinal_p2 = "+" if saldo_p2 >= 0 else ""
    st.markdown(f"""<div class="analise-card {cls}">
        <div class="kpi-label">Período 2 — Dias 16 a 31</div>
        <div style="margin-top:0.4rem; font-size:0.85rem; color:#8B8FA8;">
            Salário dia 30: <b style="color:#00D4AA">R$ {fmt_br(sal_30)}</b><br>
            Gastos 16–31: <b style="color:#FF4B6E">R$ {fmt_br(gastos_p2)}</b>
        </div>
        <div style="margin-top:0.5rem; font-size:1.2rem; font-weight:700;
            color:{'#00D4AA' if saldo_p2 >= 0 else '#FF4B6E'}">
            Saldo: {sinal_p2}R$ {fmt_br(saldo_p2)}
        </div>
    </div>""", unsafe_allow_html=True)

# Gráfico de categorias vs % da receita
linhas_analise = []
if not df_g.empty and total_receitas > 0:
    cats_df = df_g.groupby("Categoria")["Valor"].sum().reset_index().sort_values("Valor", ascending=False)
    cats_df["Pct_Receita"] = cats_df["Valor"] / total_receitas * 100
    cats_df["Cor"] = cats_df["Pct_Receita"].apply(
        lambda x: "#FF4B6E" if x > 30 else ("#FFD93D" if x > 15 else "#00D4AA")
    )

    fig_cats = go.Figure()
    fig_cats.add_trace(go.Bar(
        y=cats_df["Categoria"],
        x=cats_df["Pct_Receita"],
        orientation="h",
        marker_color=cats_df["Cor"],
        text=cats_df["Pct_Receita"].apply(lambda x: f"{x:.0f}%"),
        textposition="outside",
        textfont=dict(color="#FAFAFA"),
    ))
    fig_cats.add_vline(x=100, line_dash="dash", line_color="#FF4B6E",
                       annotation_text="Receita total", annotation_font_color="#FF4B6E")
    fig_cats.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
        xaxis_title="% da Receita", yaxis_title="",
        title="Categorias vs Receita (%)",
        title_font_size=13,
        margin=dict(t=40, b=20, l=10, r=80),
        height=max(200, len(cats_df) * 38),
        showlegend=False,
    )
    st.plotly_chart(fig_cats, use_container_width=True)

    # Gera recomendações
    pct_usado = total_gastos_v / total_receitas * 100
    if pct_usado > 100:
        linhas_analise.append(f"ALERTA: Gastos ({pct_usado:.0f}%) ultrapassaram as receitas este mês!")
    elif pct_usado > 85:
        linhas_analise.append(f"Atenção: {pct_usado:.0f}% da receita já foi consumida.")
    else:
        linhas_analise.append(f"Bom controle: {pct_usado:.0f}% da receita utilizada.")

    for _, row in cats_df.head(3).iterrows():
        eco = row["Valor"] * 0.20
        linhas_analise.append(
            f"{row['Categoria']} = {row['Pct_Receita']:.0f}% da receita — "
            f"cortar 20% economizaria R$ {fmt_br(eco, 0)}/mês."
        )

    if total_gastos_v > total_receitas:
        falta = total_gastos_v - total_receitas
        linhas_analise.append(f"Para equilibrar o mês: reduza R$ {fmt_br(falta, 0)} nos gastos acima.")

    # Mostra recomendações
    st.markdown("**📋 Recomendações**")
    for linha in linhas_analise:
        icone = "🔴" if "ALERTA" in linha or "ultrapass" in linha else ("🟡" if "Atenção" in linha else "🟢")
        st.markdown(f'<div class="rec-item">{icone} {linha}</div>', unsafe_allow_html=True)

elif df_g.empty:
    st.info("Registre gastos para ver a análise de economia.")
else:
    st.info("Registre seus salários (`salario dia 15 5000`) para ver a análise por período.")

# ── GRÁFICOS — CATEGORIA E PAGAMENTO ─────────────────────────────────────────
st.markdown('<div class="section-title">Análise de Gastos</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    if not df_g.empty:
        fig_pie = px.pie(
            df_g, values="Valor", names="Categoria", hole=0.5,
            color_discrete_sequence=px.colors.sequential.Plasma_r,
            title="Por Categoria",
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#FAFAFA",
            title_font_size=14,
            legend=dict(orientation="h", yanchor="bottom", y=-0.35, font_size=11),
            margin=dict(t=40, b=10),
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label", textfont_size=11)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Sem gastos neste mês.")

with c2:
    if not df_g.empty:
        resumo_pag = df_g.groupby("Pagamento")["Valor"].sum().reset_index().sort_values("Valor")
        fig_pag = px.bar(
            resumo_pag, y="Pagamento", x="Valor",
            orientation="h",
            color="Valor",
            color_continuous_scale=["#4B9FFF", "#FF4B6E"],
            text_auto=".2f",
            title="Por Forma de Pagamento",
        )
        fig_pag.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#FAFAFA",
            title_font_size=14,
            coloraxis_showscale=False,
            yaxis_title="", xaxis_title="R$",
            margin=dict(t=40, b=10),
        )
        fig_pag.update_traces(textfont_color="#FAFAFA")
        st.plotly_chart(fig_pag, use_container_width=True)
    else:
        st.info("Sem dados de pagamento.")

# ── GRÁFICO — EVOLUÇÃO DIÁRIA ─────────────────────────────────────────────────
if not df_g.empty:
    st.markdown('<div class="section-title">Evolução Diária de Gastos</div>', unsafe_allow_html=True)

    dias_mes = calendar.monthrange(ano_sel, mes_sel)[1]
    todos_dias = pd.DataFrame({"Dia": range(1, dias_mes + 1)})
    por_dia = df_g.groupby("Dia")["Valor"].sum().reset_index()
    por_dia = todos_dias.merge(por_dia, on="Dia", how="left").fillna(0)
    por_dia["Acumulado"] = por_dia["Valor"].cumsum()

    fig_linha = go.Figure()
    fig_linha.add_trace(go.Bar(
        x=por_dia["Dia"], y=por_dia["Valor"],
        name="Gasto Diário", marker_color="#4B9FFF", opacity=0.55,
    ))
    fig_linha.add_trace(go.Scatter(
        x=por_dia["Dia"], y=por_dia["Acumulado"],
        name="Acumulado", mode="lines+markers",
        line=dict(color="#FF4B6E", width=2.5),
        marker=dict(size=5),
    ))
    if sal_15 > 0:
        fig_linha.add_vline(x=15, line_dash="dot", line_color="#00D4AA",
                            annotation_text="Dia 15", annotation_font_color="#00D4AA",
                            annotation_position="top")
    if sal_30 > 0:
        fig_linha.add_vline(x=30, line_dash="dot", line_color="#FFD93D",
                            annotation_text="Dia 30", annotation_font_color="#FFD93D",
                            annotation_position="top")
    if total_receitas > 0:
        fig_linha.add_hline(
            y=total_receitas,
            line_dash="dash",
            line_color="#00D4AA",
            annotation_text=f"Receita R$ {fmt_br(total_receitas, 0)}",
            annotation_font_color="#00D4AA",
            annotation_position="top right",
        )
    fig_linha.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
        legend=dict(orientation="h", y=1.08),
        xaxis_title="Dia do Mês",
        yaxis_title="R$",
        hovermode="x unified",
        margin=dict(t=10, b=30),
    )
    st.plotly_chart(fig_linha, use_container_width=True)

# ── TENDÊNCIA HISTÓRICA (opcional) ────────────────────────────────────────────
if mostrar_historico and not df_gastos.empty:
    st.markdown('<div class="section-title">Tendência Histórica</div>', unsafe_allow_html=True)

    mensal_g = df_gastos.groupby(["Ano", "Mes"])["Valor"].sum().reset_index()
    mensal_g["Periodo"] = mensal_g.apply(lambda r: f"{r['Mes']:02d}/{r['Ano']}", axis=1)
    mensal_g = mensal_g.sort_values(["Ano", "Mes"])

    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(
        x=mensal_g["Periodo"], y=mensal_g["Valor"],
        name="Gastos", mode="lines+markers",
        line=dict(color="#FF4B6E", width=2.5),
        fill="tozeroy", fillcolor="rgba(255,75,110,0.1)",
    ))

    if not df_proventos.empty:
        mensal_p = df_proventos.groupby(["Ano", "Mes"])["Valor"].sum().reset_index()
        mensal_p["Periodo"] = mensal_p.apply(lambda r: f"{r['Mes']:02d}/{r['Ano']}", axis=1)
        mensal_p = mensal_p.sort_values(["Ano", "Mes"])
        fig_hist.add_trace(go.Scatter(
            x=mensal_p["Periodo"], y=mensal_p["Valor"],
            name="Receitas", mode="lines+markers",
            line=dict(color="#00D4AA", width=2, dash="dot"),
        ))

    fig_hist.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#FAFAFA",
        xaxis_title="Mês", yaxis_title="R$",
        legend=dict(orientation="h", y=1.08),
        margin=dict(t=10, b=30),
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# ── PROVENTOS + TABELA DETALHADA ──────────────────────────────────────────────
st.markdown('<div class="section-title">Detalhes do Mês</div>', unsafe_allow_html=True)

col_p, col_g = st.columns([1, 2])

with col_p:
    st.subheader("💵 Receitas")
    if df_p.empty:
        st.info("Nenhuma receita registrada.\n\nEnvie no Telegram:\n`salario dia 15 5000`")
    else:
        for _, row in df_p.sort_values("Valor", ascending=False).iterrows():
            if pd.notna(row["Dia"]) and row["Dia"]:
                dia_label = f"dia {int(row['Dia'])}"
            else:
                dia_label = row["Data"].strftime("%d/%m")
            st.markdown(f"""<div class="provento-row">
                <span>
                    <span class="provento-desc">{row['Descricao']}</span>
                    <span class="provento-dia">({dia_label})</span>
                </span>
                <span class="provento-val">R$ {fmt_br(row['Valor'])}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown(f"**Total: R$ {fmt_br(df_p['Valor'].sum())}**")

with col_g:
    st.subheader("📋 Gastos")
    if df_g.empty:
        st.info("Nenhum gasto registrado neste mês.")
    else:
        df_exib = df_g[["Data", "Categoria", "Valor", "Pagamento"]].copy()
        df_exib["Valor"] = df_exib["Valor"].apply(lambda v: f"R$ {fmt_br(v)}")
        st.dataframe(
            df_exib.sort_values("Data", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Data": st.column_config.DatetimeColumn("Data", format="DD/MM HH:mm"),
                "Valor": st.column_config.TextColumn("Valor (R$)"),
            },
        )

# ── PAINEL DE EXCLUSÃO (sidebar) ─────────────────────────────────────────────
with st.sidebar.expander("🗑️ Excluir Lançamento"):
    tipo_del = st.radio("Tipo", ["Gasto", "Receita"], horizontal=True, key="tipo_del")

    if tipo_del == "Gasto":
        df_del = df_g.copy() if not df_g.empty else pd.DataFrame()
        col_desc = "Categoria"
    else:
        df_del = df_p.copy() if not df_p.empty else pd.DataFrame()
        col_desc = "Descricao"

    if df_del.empty:
        st.caption("Nenhum lançamento neste mês.")
    else:
        opcoes_del = {
            f"{row['Data'].strftime('%d/%m %H:%M')} — {row[col_desc]} — R$ {fmt_br(row['Valor'])}": row["id"]
            for _, row in df_del.sort_values("Data", ascending=False).iterrows()
        }
        sel_label = st.selectbox("Selecionar", list(opcoes_del.keys()), key="sel_del")
        sel_id = opcoes_del[sel_label]

        st.warning(f"⚠️ Isso excluirá permanentemente o registro selecionado.")
        if st.button("🗑️ Confirmar Exclusão", key="btn_del", type="primary", use_container_width=True):
            if tipo_del == "Gasto":
                ok = deletar_gasto(sel_id)
            else:
                ok = deletar_provento(sel_id)
            if ok:
                st.success("Excluído com sucesso!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Erro ao excluir.")

st.sidebar.markdown("---")

# ── BOTÃO EXPORTAR PDF (sidebar, após dados computados) ──────────────────────
pdf_bytes = gerar_pdf(
    MESES_PT[mes_sel], ano_sel,
    df_g, df_p,
    total_receitas, total_gastos_v, saldo,
    linhas_analise,
)
st.sidebar.download_button(
    label="📄 Exportar PDF",
    data=pdf_bytes,
    file_name=f"financas_{MESES_PT[mes_sel]}_{ano_sel}.pdf",
    mime="application/pdf",
    use_container_width=True,
)
