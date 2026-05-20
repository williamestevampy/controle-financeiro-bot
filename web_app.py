import os
from datetime import datetime
from collections import defaultdict

from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from dotenv import load_dotenv

from database import SessionLocal, engine
import models
from pdf_generator import gerar_pdf

load_dotenv()
models.Base.metadata.create_all(bind=engine)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-troque-em-producao")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")
_signer = URLSafeTimedSerializer(SECRET_KEY)
_SESSION_MAX_AGE = 30 * 24 * 3600  # 30 dias

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

app = FastAPI(docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _is_authed(request: Request) -> bool:
    token = request.cookies.get("session")
    if not token:
        return False
    try:
        _signer.loads(token, max_age=_SESSION_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def _redirect_login():
    return RedirectResponse("/login", status_code=302)


def _opcoes_meses():
    hoje = datetime.now()
    opcoes = []
    for i in range(12):
        mes = hoje.month - i
        ano = hoje.year
        while mes <= 0:
            mes += 12
            ano -= 1
        opcoes.append({"label": f"{MESES_PT[mes]} {ano}", "mes": mes, "ano": ano})
    return opcoes


def _gerar_analise(cats: list, total_receitas: float, total_gastos: float, saldo: float, gastos: list) -> list:
    alertas = []

    if not gastos:
        return alertas

    # Saldo geral
    if total_receitas == 0:
        alertas.append({"tipo": "warn", "titulo": "Sem receitas registradas", "msg": "Registre seus proventos para ver a análise completa."})
        return alertas

    pct_gasto = total_gastos / total_receitas * 100

    if saldo < 0:
        alertas.append({"tipo": "danger", "titulo": "⚠️ Gastos acima da renda", "msg": f"Você gastou R$ {abs(saldo):.2f} a mais do que recebeu este mês. Corte gastos com urgência."})
    elif pct_gasto > 90:
        alertas.append({"tipo": "warn", "titulo": "🔶 Quase no limite", "msg": f"Você usou {pct_gasto:.0f}% da sua renda. Sobrou apenas R$ {saldo:.2f}. Atenção nos próximos gastos."})
    else:
        alertas.append({"tipo": "ok", "titulo": "✅ Saldo positivo", "msg": f"Você está guardando {100 - pct_gasto:.0f}% da renda (R$ {saldo:.2f}). Continue assim!"})

    # Análise por categoria
    for cat, val in cats[:8]:
        pct = val / total_receitas * 100
        if pct > 30:
            alertas.append({"tipo": "danger", "titulo": f"🔴 {cat} — {pct:.0f}% da renda", "msg": f"R$ {val:.2f} gastos. Esta categoria está consumindo mais de 30% da sua renda. Considere reduzir."})
        elif pct > 15:
            alertas.append({"tipo": "warn", "titulo": f"🟡 {cat} — {pct:.0f}% da renda", "msg": f"R$ {val:.2f} gastos. Acima de 15% da renda — fique de olho nesta categoria."})

    # Análise por período (1-15 vs 16-31)
    gastos_p1 = sum(g.valor for g in gastos if g.data_hora.day <= 15)
    gastos_p2 = sum(g.valor for g in gastos if g.data_hora.day > 15)
    if gastos_p1 > 0 and gastos_p2 > 0:
        if gastos_p1 > gastos_p2 * 1.5:
            alertas.append({"tipo": "warn", "titulo": "📅 Gastos concentrados no início do mês", "msg": f"Dias 1-15: R$ {gastos_p1:.2f} vs dias 16-31: R$ {gastos_p2:.2f}. Distribua melhor os gastos ao longo do mês."})
        elif gastos_p2 > gastos_p1 * 1.5:
            alertas.append({"tipo": "warn", "titulo": "📅 Gastos concentrados no fim do mês", "msg": f"Dias 16-31: R$ {gastos_p2:.2f} vs dias 1-15: R$ {gastos_p1:.2f}. Atenção com os gastos na segunda quinzena."})

    # Categoria top — sugestão de corte
    if cats:
        top_cat, top_val = cats[0]
        top_pct = top_val / total_gastos * 100
        if top_pct > 40:
            alertas.append({"tipo": "warn", "titulo": f"💡 Maior gasto: {top_cat}", "msg": f"Representa {top_pct:.0f}% de todos os seus gastos (R$ {top_val:.2f}). Reduzir esta categoria teria maior impacto na sua economia."})

    return alertas


def _carregar_dados(db: Session, ano: int, mes: int) -> dict:
    inicio = datetime(ano, mes, 1)
    fim = datetime(ano + 1, 1, 1) if mes == 12 else datetime(ano, mes + 1, 1)

    gastos = db.query(models.Gasto).filter(
        models.Gasto.data_hora >= inicio,
        models.Gasto.data_hora < fim,
    ).order_by(desc(models.Gasto.data_hora)).all()

    proventos = db.query(models.Provento).filter(
        models.Provento.data_hora >= inicio,
        models.Provento.data_hora < fim,
    ).order_by(models.Provento.data_hora).all()

    total_gastos = sum(g.valor for g in gastos)
    total_receitas = sum(p.valor for p in proventos)
    saldo = total_receitas - total_gastos

    cats: dict[str, float] = defaultdict(float)
    pagamentos: dict[str, float] = defaultdict(float)
    por_dia: dict[int, float] = defaultdict(float)
    for g in gastos:
        cats[g.categoria] += g.valor
        pagamentos[g.forma_pagamento] += g.valor
        por_dia[g.data_hora.day] += g.valor

    cats_sorted = sorted(cats.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_receitas": total_receitas,
        "total_gastos": total_gastos,
        "saldo": saldo,
        "n_trans": len(gastos),
        "gastos": gastos,
        "proventos": proventos,
        "cats": cats_sorted,
        "pagamentos": sorted(pagamentos.items(), key=lambda x: x[1], reverse=True),
        "por_dia": sorted(por_dia.items()),
        "alertas": _gerar_analise(cats_sorted, total_receitas, total_gastos, saldo, gastos),
    }


# ─── Login ────────────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if _is_authed(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html", context={"erro": False})


@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, senha: str = Form(...)):
    if senha == DASHBOARD_PASSWORD:
        token = _signer.dumps("autenticado")
        response = RedirectResponse("/", status_code=303)
        response.set_cookie("session", token, max_age=_SESSION_MAX_AGE, httponly=True, samesite="lax")
        return response
    return templates.TemplateResponse(request=request, name="login.html", context={"erro": True})


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("session")
    return response


# ─── Dashboard tabs ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def inicio(request: Request, mes: int = 0, ano: int = 0, db: Session = Depends(get_db)):
    if not _is_authed(request):
        return _redirect_login()

    hoje = datetime.now()
    if mes == 0:
        mes = hoje.month
    if ano == 0:
        ano = hoje.year

    dados = _carregar_dados(db, ano, mes)
    return templates.TemplateResponse(request=request, name="inicio.html", context={
        "tab": "inicio",
        "mes": mes,
        "ano": ano,
        "mes_nome": MESES_PT[mes],
        "opcoes_meses": _opcoes_meses(),
        **dados,
    })


@app.get("/analise", response_class=HTMLResponse)
async def analise(request: Request, mes: int = 0, ano: int = 0, db: Session = Depends(get_db)):
    if not _is_authed(request):
        return _redirect_login()

    hoje = datetime.now()
    if mes == 0:
        mes = hoje.month
    if ano == 0:
        ano = hoje.year

    dados = _carregar_dados(db, ano, mes)
    return templates.TemplateResponse(request=request, name="analise.html", context={
        "tab": "analise",
        "mes": mes,
        "ano": ano,
        "mes_nome": MESES_PT[mes],
        "opcoes_meses": _opcoes_meses(),
        **dados,
    })


@app.get("/receitas", response_class=HTMLResponse)
async def receitas(request: Request, mes: int = 0, ano: int = 0, db: Session = Depends(get_db)):
    if not _is_authed(request):
        return _redirect_login()

    hoje = datetime.now()
    if mes == 0:
        mes = hoje.month
    if ano == 0:
        ano = hoje.year

    dados = _carregar_dados(db, ano, mes)
    return templates.TemplateResponse(request=request, name="receitas.html", context={
        "tab": "receitas",
        "mes": mes,
        "ano": ano,
        "mes_nome": MESES_PT[mes],
        "opcoes_meses": _opcoes_meses(),
        **dados,
    })


@app.get("/relatorio", response_class=HTMLResponse)
async def relatorio(request: Request, mes: int = 0, ano: int = 0, db: Session = Depends(get_db)):
    if not _is_authed(request):
        return _redirect_login()

    hoje = datetime.now()
    if mes == 0:
        mes = hoje.month
    if ano == 0:
        ano = hoje.year

    dados = _carregar_dados(db, ano, mes)
    return templates.TemplateResponse(request=request, name="relatorio.html", context={
        "tab": "relatorio",
        "mes": mes,
        "ano": ano,
        "mes_nome": MESES_PT[mes],
        "opcoes_meses": _opcoes_meses(),
        **dados,
    })


# ─── API dados (JSON para Chart.js) ──────────────────────────────────────────

@app.get("/api/dados/{ano}/{mes}")
async def api_dados(ano: int, mes: int, request: Request, db: Session = Depends(get_db)):
    if not _is_authed(request):
        raise HTTPException(status_code=401)

    d = _carregar_dados(db, ano, mes)
    return {
        "total_receitas": d["total_receitas"],
        "total_gastos": d["total_gastos"],
        "saldo": d["saldo"],
        "n_trans": d["n_trans"],
        "cats": [{"cat": c, "val": v} for c, v in d["cats"]],
        "pagamentos": [{"forma": f, "val": v} for f, v in d["pagamentos"]],
        "por_dia": [{"dia": dia, "val": v} for dia, v in d["por_dia"]],
        "gastos": [
            {
                "id": g.id,
                "data": g.data_hora.strftime("%d/%m"),
                "categoria": g.categoria,
                "valor": g.valor,
                "pagamento": g.forma_pagamento,
            }
            for g in d["gastos"][:20]
        ],
    }


# ─── Ações ───────────────────────────────────────────────────────────────────

@app.post("/provento")
async def salvar_provento(
    request: Request,
    descricao: str = Form(...),
    valor: float = Form(...),
    dia: str = Form(""),
    mes: int = Form(0),
    ano: int = Form(0),
    db: Session = Depends(get_db),
):
    if not _is_authed(request):
        return _redirect_login()

    dia_int = int(dia) if dia.strip().isdigit() else None
    db.add(models.Provento(descricao=descricao.strip().capitalize(), valor=valor, dia=dia_int))
    db.commit()

    hoje = datetime.now()
    m = mes or hoje.month
    a = ano or hoje.year
    return RedirectResponse(f"/receitas?mes={m}&ano={a}", status_code=302)


@app.post("/gasto/{gasto_id}/delete")
async def deletar_gasto(
    gasto_id: int,
    request: Request,
    mes: int = Form(0),
    ano: int = Form(0),
    db: Session = Depends(get_db),
):
    if not _is_authed(request):
        return _redirect_login()

    obj = db.query(models.Gasto).filter(models.Gasto.id == gasto_id).first()
    if obj:
        db.delete(obj)
        db.commit()

    hoje = datetime.now()
    m = mes or hoje.month
    a = ano or hoje.year
    return RedirectResponse(f"/?mes={m}&ano={a}", status_code=302)


@app.post("/provento/{provento_id}/delete")
async def deletar_provento(
    provento_id: int,
    request: Request,
    mes: int = Form(0),
    ano: int = Form(0),
    db: Session = Depends(get_db),
):
    if not _is_authed(request):
        return _redirect_login()

    obj = db.query(models.Provento).filter(models.Provento.id == provento_id).first()
    if obj:
        db.delete(obj)
        db.commit()

    hoje = datetime.now()
    m = mes or hoje.month
    a = ano or hoje.year
    return RedirectResponse(f"/receitas?mes={m}&ano={a}", status_code=302)


# ─── PDF ─────────────────────────────────────────────────────────────────────

@app.get("/relatorio/pdf")
async def download_pdf(request: Request, mes: int = 0, ano: int = 0, db: Session = Depends(get_db)):
    if not _is_authed(request):
        return _redirect_login()

    hoje = datetime.now()
    m = mes or hoje.month
    a = ano or hoje.year

    pdf_bytes = gerar_pdf(db, a, m)
    nome = f"relatorio_{a}_{m:02d}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nome}"},
    )


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/ping")
def ping():
    return {"ok": True}
