import io
from datetime import datetime
from sqlalchemy.orm import Session
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import models

_NL = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def _fmt(v: float) -> str:
    s = f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_pdf(db: Session, ano: int, mes: int) -> bytes:
    inicio = datetime(ano, mes, 1)
    fim = datetime(ano + 1, 1, 1) if mes == 12 else datetime(ano, mes + 1, 1)

    gastos = db.query(models.Gasto).filter(
        models.Gasto.data_hora >= inicio,
        models.Gasto.data_hora < fim,
    ).order_by(models.Gasto.data_hora.desc()).all()

    proventos = db.query(models.Provento).filter(
        models.Provento.data_hora >= inicio,
        models.Provento.data_hora < fim,
    ).order_by(models.Provento.data_hora).all()

    total_gastos = sum(g.valor for g in gastos)
    total_receitas = sum(p.valor for p in proventos)
    saldo = total_receitas - total_gastos
    mes_nome = MESES_PT[mes]

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Cabeçalho
    pdf.set_fill_color(13, 13, 20)
    pdf.rect(0, 0, 210, 30, "F")
    pdf.set_text_color(250, 250, 250)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_y(8)
    pdf.cell(0, 10, f"Relatorio Financeiro - {mes_nome} {ano}", align="C", **_NL)
    pdf.set_y(35)
    pdf.set_text_color(30, 30, 30)

    # KPIs
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(240, 240, 245)
    pdf.cell(0, 8, "Resumo do Mes", **_NL, fill=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(1)
    pdf.cell(60, 7, "Receitas:")
    pdf.set_text_color(0, 140, 100)
    pdf.cell(0, 7, f"R$ {_fmt(total_receitas)}", **_NL)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(60, 7, "Gastos:")
    pdf.set_text_color(200, 40, 60)
    pdf.cell(0, 7, f"R$ {_fmt(total_gastos)}", **_NL)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(60, 7, "Saldo:")
    cor = (0, 140, 100) if saldo >= 0 else (200, 40, 60)
    pdf.set_text_color(*cor)
    sinal = "+" if saldo >= 0 else ""
    pdf.cell(0, 7, f"{sinal}R$ {_fmt(saldo)}", **_NL)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(4)

    # Proventos
    if proventos:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(240, 240, 245)
        pdf.cell(0, 8, "Receitas do Mes", **_NL, fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.ln(1)
        for p in proventos:
            dia_txt = f"dia {p.dia}" if p.dia else p.data_hora.strftime("%d/%m")
            desc = str(p.descricao)[:40]
            pdf.cell(100, 6, f"  {desc} ({dia_txt})")
            pdf.cell(0, 6, f"R$ {_fmt(p.valor)}", **_NL)
        pdf.ln(3)

    # Gastos por categoria
    if gastos:
        cats: dict[str, float] = {}
        for g in gastos:
            cats[g.categoria] = cats.get(g.categoria, 0) + g.valor
        cats_sorted = sorted(cats.items(), key=lambda x: x[1], reverse=True)

        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(240, 240, 245)
        pdf.cell(0, 8, "Gastos por Categoria", **_NL, fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.ln(1)
        for cat, val in cats_sorted:
            pct = val / total_gastos * 100 if total_gastos > 0 else 0
            pdf.cell(100, 6, f"  {str(cat)[:40]}")
            pdf.cell(40, 6, f"R$ {_fmt(val)}")
            pdf.cell(0, 6, f"({pct:.0f}%)", **_NL)
        pdf.ln(3)

    # Histórico detalhado
    if gastos:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(240, 240, 245)
        pdf.cell(0, 8, "Historico de Gastos (ultimos 50)", **_NL, fill=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.ln(1)
        for g in gastos[:50]:
            data_str = g.data_hora.strftime("%d/%m")
            cat = str(g.categoria)[:25]
            pag = str(g.forma_pagamento)[:12]
            linha = f"  {data_str}  {cat:<25}  R$ {g.valor:>8.2f}  {pag}"
            linha_safe = linha.encode("latin-1", errors="replace").decode("latin-1")
            pdf.set_x(pdf.l_margin)
            pdf.cell(pdf.epw, 5, linha_safe, **_NL)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
