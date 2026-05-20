import os
import re
import requests
import models
from fastapi import FastAPI, Request, Depends
from database import SessionLocal, engine
from sqlalchemy.orm import Session
from sqlalchemy import desc
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

models.Base.metadata.create_all(bind=engine)

def parse_valor_br(texto):
    """Converte número no formato BR para float: 1.307,42→1307.42, 1.520→1520.0"""
    s = texto.strip().replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif "." in s:
        partes = s.split(".")
        if len(partes) == 2 and len(partes[1]) == 3:
            s = s.replace(".", "")  # separador de milhar ex: 1.520
    return float(s)

app = FastAPI()

TOKEN = os.getenv("TELEGRAM_TOKEN")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def enviar_mensagem(chat_id, texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"})

@app.get("/ping")
def ping():
    return {"v": "fix-salario-v4", "ok": True}

@app.post("/webhook")
async def receber_mensagem(request: Request, db: Session = Depends(get_db)):
    dados = await request.json()

    if "message" in dados and "text" in dados["message"]:
        texto_original = dados["message"]["text"]
        texto_limpo = texto_original.lower()
        chat_id = dados["message"]["chat"]["id"]

        # /start
        if texto_limpo == "/start":
            msg = (
                "🚀 *Bot Financeiro Pro*\n\n"
                "*Registrar gasto:*\n"
                "`40,88 mercado credito`\n"
                "`15 lanche pix`\n\n"
                "*Comandos:*\n"
                "/extrato — últimos gastos + saldo do mês\n"
                "/mensal — resumo por categoria\n"
                "/proventos — receitas do mês\n\n"
                "*Registrar salário:*\n"
                "`salario dia 15 5000`\n"
                "`salario dia 30 3000`\n\n"
                "*Outros proventos:*\n"
                "`/provento Freelance 1200`"
            )
            enviar_mensagem(chat_id, msg)
            return {"status": "ok"}

        # /extrato — últimos 10 gastos + saldo mensal
        if texto_limpo == "/extrato":
            agora = datetime.now()
            inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            gastos_recentes = db.query(models.Gasto).order_by(desc(models.Gasto.data_hora)).limit(10).all()
            gastos_mes = db.query(models.Gasto).filter(models.Gasto.data_hora >= inicio_mes).all()
            proventos_mes = db.query(models.Provento).filter(models.Provento.data_hora >= inicio_mes).all()

            total_gastos = sum(g.valor for g in gastos_mes)
            total_proventos = sum(p.valor for p in proventos_mes)
            saldo = total_proventos - total_gastos
            sinal = "+" if saldo >= 0 else ""

            msg = f"📊 *Resumo {agora.strftime('%m/%Y')}*\n"
            msg += f"💵 Receitas: R$ {total_proventos:.2f}\n"
            msg += f"💸 Gastos: R$ {total_gastos:.2f}\n"
            msg += f"💰 Saldo: {sinal}R$ {saldo:.2f}\n\n"
            msg += "📋 *Últimos 10 Gastos*\n\n"

            if not gastos_recentes:
                msg += "Nenhum gasto registrado."
            else:
                for g in gastos_recentes:
                    msg += f"• {g.data_hora.strftime('%d/%m')} - {g.categoria}: *R$ {g.valor:.2f}* ({g.forma_pagamento})\n"

            enviar_mensagem(chat_id, msg)
            return {"status": "ok"}

        # /mensal — resumo por categoria do mês atual
        if texto_limpo in ("/mensal", "/mes"):
            agora = datetime.now()
            inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            gastos_mes = db.query(models.Gasto).filter(models.Gasto.data_hora >= inicio_mes).all()
            proventos_mes = db.query(models.Provento).filter(models.Provento.data_hora >= inicio_mes).all()

            total_gastos = sum(g.valor for g in gastos_mes)
            total_proventos = sum(p.valor for p in proventos_mes)
            saldo = total_proventos - total_gastos
            sinal = "+" if saldo >= 0 else ""

            cats = {}
            for g in gastos_mes:
                cats[g.categoria] = cats.get(g.categoria, 0) + g.valor
            cats_sorted = sorted(cats.items(), key=lambda x: x[1], reverse=True)

            msg = f"📅 *Resumo Mensal - {agora.strftime('%m/%Y')}*\n\n"
            msg += f"💵 *Receitas:* R$ {total_proventos:.2f}\n"
            msg += f"💸 *Gastos:* R$ {total_gastos:.2f}\n"
            msg += f"💰 *Saldo:* {sinal}R$ {saldo:.2f}\n\n"

            if cats_sorted:
                msg += "*Gastos por Categoria:*\n"
                for cat, val in cats_sorted[:8]:
                    pct = (val / total_gastos * 100) if total_gastos > 0 else 0
                    msg += f"  • {cat}: R$ {val:.2f} ({pct:.0f}%)\n"

            enviar_mensagem(chat_id, msg)
            return {"status": "ok"}

        # /proventos — lista receitas do mês atual
        if texto_limpo == "/proventos":
            agora = datetime.now()
            inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            proventos = db.query(models.Provento).filter(
                models.Provento.data_hora >= inicio_mes
            ).order_by(models.Provento.data_hora).all()

            if not proventos:
                enviar_mensagem(chat_id, "Nenhum provento registrado este mês.\n\nUse: `salario dia 15 5000`")
            else:
                total = sum(p.valor for p in proventos)
                msg = f"💵 *Proventos de {agora.strftime('%m/%Y')}*\n\n"
                for p in proventos:
                    dia_str = f" (dia {p.dia})" if p.dia else ""
                    msg += f"• {p.descricao}{dia_str}: *R$ {p.valor:.2f}*\n"
                msg += f"\n*Total: R$ {total:.2f}*"
                enviar_mensagem(chat_id, msg)
            return {"status": "ok"}

        # /provento <desc> <valor> [dia N] — registra receita
        if texto_limpo.startswith("/provento "):
            partes = texto_original[10:].strip()

            dia = None
            match_dia = re.search(r'\bdia\s+(\d{1,2})\b', partes, re.IGNORECASE)
            if match_dia:
                dia = int(match_dia.group(1))
                partes = re.sub(r'\bdia\s+\d{1,2}\b', '', partes, flags=re.IGNORECASE).strip()

            match_valor = re.search(r'(\d+[\.,]\d+|\d+)', partes)
            if not match_valor:
                enviar_mensagem(chat_id, "Formato inválido. Use: `/provento Salario 5000 dia 15`")
                return {"status": "ok"}

            valor_texto = match_valor.group(1)
            valor = float(valor_texto.replace(",", "."))

            descricao = partes.replace(valor_texto, "").strip().capitalize()
            if not descricao:
                descricao = "Provento"

            novo = models.Provento(descricao=descricao, valor=valor, dia=dia)
            db.add(novo)
            db.commit()

            dia_str = f" (dia {dia})" if dia else ""
            enviar_mensagem(chat_id, f"✅ *Provento Salvo!*\n💵 R$ {valor:.2f}\n📝 {descricao}{dia_str}")
            return {"status": "ok"}

        # "salario/salário" em qualquer posição = sempre receita, nunca gasto
        if "salar" in texto_limpo:
            match_dia = re.search(r'\bdia\s+(\d{1,2})\b', texto_limpo)
            if not match_dia:
                enviar_mensagem(chat_id, "Informe o dia: `Salario dia 15 1520`")
                return {"status": "ok"}

            dia = int(match_dia.group(1))

            # Valor vem preferencialmente do texto APÓS "dia N"
            _regex_val = r'(\d{1,3}\.\d{3},\d+|\d{1,3}\.\d{3}|\d+,\d+|\d+)'
            texto_apos_dia = texto_original[match_dia.end():]
            match_val = re.search(_regex_val, texto_apos_dia)
            # Fallback: se nada após o dia, busca no texto completo sem o número do dia
            if not match_val:
                texto_sem_dia = re.sub(r'\bdia\s+\d{1,2}\b', '', texto_original, flags=re.IGNORECASE)
                match_val = re.search(_regex_val, texto_sem_dia)
            if not match_val:
                enviar_mensagem(chat_id, "Informe o valor: `Salario dia 15 1520`")
                return {"status": "ok"}

            valor = parse_valor_br(match_val.group(1))
            novo = models.Provento(descricao="Salário", valor=valor, dia=dia)
            db.add(novo)
            db.commit()
            enviar_mensagem(chat_id, f"✅ *Salário Salvo!*\n💵 R$ {valor:,.2f}\n📅 Dia {dia}")
            return {"status": "ok"}

        # Parsing de gasto por linguagem natural
        pagamento = "Dinheiro"
        if "pix" in texto_limpo:
            pagamento = "Pix"
        elif "debito" in texto_limpo or "débito" in texto_limpo:
            pagamento = "Débito"
        elif any(p in texto_limpo for p in ["credito", "crédito", "cartao", "cartão"]):
            pagamento = "Crédito"

        busca_valor = re.search(r'(\d+[\.,]\s?\d+|\d+)', texto_original)

        if busca_valor:
            valor_texto = busca_valor.group(1)
            valor_limpo = valor_texto.replace(" ", "").replace(",", ".")
            valor = float(valor_limpo)

            categoria = texto_original.replace(valor_texto, "")
            termos_remover = [
                "debito", "débito", "credito", "crédito",
                "pix", "dinheiro", "cartao", "cartão", "ifood"
            ]
            for t in termos_remover:
                categoria = re.sub(t, "", categoria, flags=re.IGNORECASE)

            categoria = categoria.strip().capitalize()
            if not categoria:
                categoria = "Outros"

            novo_gasto = models.Gasto(valor=valor, categoria=categoria, forma_pagamento=pagamento)
            db.add(novo_gasto)
            db.commit()

            enviar_mensagem(chat_id, f"✅ *Salvo com Sucesso!*\n💰 R$ {valor:.2f}\n🏷️ {categoria}\n💳 {pagamento}")
        else:
            enviar_mensagem(chat_id, "❓ Não encontrei o valor. Tente algo como: `50.00 lanche cartao`.")

    return {"status": "ok"}
