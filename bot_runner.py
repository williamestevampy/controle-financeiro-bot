import os
import re
import time
import requests
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy import desc
from database import SessionLocal
import models

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE  = f"https://api.telegram.org/bot{TOKEN}"


def parse_valor_br(texto):
    s = texto.strip().replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif "." in s:
        partes = s.split(".")
        if len(partes) == 2 and len(partes[1]) == 3:
            s = s.replace(".", "")
    return float(s)


def enviar(chat_id, texto):
    requests.post(f"{BASE}/sendMessage",
                  json={"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"},
                  timeout=10)


def processar(msg):
    texto_original = msg.get("text", "")
    if not texto_original:
        return

    texto_limpo = texto_original.lower()
    chat_id     = msg["chat"]["id"]
    db          = SessionLocal()

    try:
        # /start
        if texto_limpo == "/start":
            enviar(chat_id,
                "🚀 *Bot Financeiro Pro*\n\n"
                "*Registrar gasto:*\n"
                "`40,88 mercado credito`\n"
                "`15 lanche pix`\n\n"
                "*Comandos:*\n"
                "/extrato — últimos gastos + saldo do mês\n"
                "/mensal — resumo por categoria\n"
                "/proventos — receitas do mês\n\n"
                "*Registrar salário:*\n"
                "`Salario dia 15 1520`\n"
                "`Salario dia 30 1307,42`\n\n"
                "*Outros proventos:*\n"
                "`/provento Freelance 1200`"
            )
            return

        # /extrato
        if texto_limpo == "/extrato":
            agora      = datetime.now()
            inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            g_rec  = db.query(models.Gasto).order_by(desc(models.Gasto.data_hora)).limit(10).all()
            g_mes  = db.query(models.Gasto).filter(models.Gasto.data_hora >= inicio_mes).all()
            p_mes  = db.query(models.Provento).filter(models.Provento.data_hora >= inicio_mes).all()
            tg = sum(g.valor for g in g_mes)
            tp = sum(p.valor for p in p_mes)
            sd = tp - tg
            sinal = "+" if sd >= 0 else ""
            msg_txt  = f"📊 *Resumo {agora.strftime('%m/%Y')}*\n"
            msg_txt += f"💵 Receitas: R$ {tp:.2f}\n"
            msg_txt += f"💸 Gastos: R$ {tg:.2f}\n"
            msg_txt += f"💰 Saldo: {sinal}R$ {sd:.2f}\n\n"
            msg_txt += "📋 *Últimos 10 Gastos*\n\n"
            if not g_rec:
                msg_txt += "Nenhum gasto registrado."
            else:
                for g in g_rec:
                    msg_txt += f"• {g.data_hora.strftime('%d/%m')} - {g.categoria}: *R$ {g.valor:.2f}* ({g.forma_pagamento})\n"
            enviar(chat_id, msg_txt)
            return

        # /mensal
        if texto_limpo in ("/mensal", "/mes"):
            agora      = datetime.now()
            inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            g_mes = db.query(models.Gasto).filter(models.Gasto.data_hora >= inicio_mes).all()
            p_mes = db.query(models.Provento).filter(models.Provento.data_hora >= inicio_mes).all()
            tg = sum(g.valor for g in g_mes)
            tp = sum(p.valor for p in p_mes)
            sd = tp - tg
            sinal = "+" if sd >= 0 else ""
            cats = {}
            for g in g_mes:
                cats[g.categoria] = cats.get(g.categoria, 0) + g.valor
            cats_sorted = sorted(cats.items(), key=lambda x: x[1], reverse=True)
            msg_txt  = f"📅 *Resumo Mensal - {agora.strftime('%m/%Y')}*\n\n"
            msg_txt += f"💵 *Receitas:* R$ {tp:.2f}\n"
            msg_txt += f"💸 *Gastos:* R$ {tg:.2f}\n"
            msg_txt += f"💰 *Saldo:* {sinal}R$ {sd:.2f}\n\n"
            if cats_sorted:
                msg_txt += "*Gastos por Categoria:*\n"
                for cat, val in cats_sorted[:8]:
                    pct = (val / tg * 100) if tg > 0 else 0
                    msg_txt += f"  • {cat}: R$ {val:.2f} ({pct:.0f}%)\n"
            enviar(chat_id, msg_txt)
            return

        # /proventos
        if texto_limpo == "/proventos":
            agora      = datetime.now()
            inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            provs = db.query(models.Provento).filter(
                models.Provento.data_hora >= inicio_mes
            ).order_by(models.Provento.data_hora).all()
            if not provs:
                enviar(chat_id, "Nenhum provento este mês.\n\nUse: `Salario dia 15 1520`")
            else:
                total   = sum(p.valor for p in provs)
                msg_txt = f"💵 *Proventos de {agora.strftime('%m/%Y')}*\n\n"
                for p in provs:
                    dia_str = f" (dia {p.dia})" if p.dia else ""
                    msg_txt += f"• {p.descricao}{dia_str}: *R$ {p.valor:.2f}*\n"
                msg_txt += f"\n*Total: R$ {total:.2f}*"
                enviar(chat_id, msg_txt)
            return

        # /provento <desc> <valor> [dia N]
        if texto_limpo.startswith("/provento "):
            partes = texto_original[10:].strip()
            dia = None
            m_dia = re.search(r'\bdia\s+(\d{1,2})\b', partes, re.IGNORECASE)
            if m_dia:
                dia = int(m_dia.group(1))
                partes = re.sub(r'\bdia\s+\d{1,2}\b', '', partes, flags=re.IGNORECASE).strip()
            m_val = re.search(r'(\d+[\.,]\d+|\d+)', partes)
            if not m_val:
                enviar(chat_id, "Formato invalido. Use: `/provento Freelance 1200`")
                return
            valor    = float(m_val.group(1).replace(",", "."))
            descricao = partes.replace(m_val.group(1), "").strip().capitalize() or "Provento"
            db.add(models.Provento(descricao=descricao, valor=valor, dia=dia))
            db.commit()
            dia_str = f" (dia {dia})" if dia else ""
            enviar(chat_id, f"✅ *Provento Salvo!*\n💵 R$ {valor:.2f}\n📝 {descricao}{dia_str}")
            return

        # Salário: "Salario dia 15 1520" — sempre receita, nunca gasto
        if "salar" in texto_limpo:
            m_dia = re.search(r'\bdia\s+(\d{1,2})\b', texto_limpo)
            if not m_dia:
                enviar(chat_id, "Informe o dia: `Salario dia 15 1520`")
                return
            dia = int(m_dia.group(1))
            _rv  = r'(\d{1,3}\.\d{3},\d+|\d{1,3}\.\d{3}|\d+,\d+|\d+)'
            # Valor preferencialmente APÓS "dia N"
            m_val = re.search(_rv, texto_original[m_dia.end():])
            if not m_val:
                sem_dia = re.sub(r'\bdia\s+\d{1,2}\b', '', texto_original, flags=re.IGNORECASE)
                m_val = re.search(_rv, sem_dia)
            if not m_val:
                enviar(chat_id, "Informe o valor: `Salario dia 15 1520`")
                return
            valor = parse_valor_br(m_val.group(1))
            db.add(models.Provento(descricao="Salário", valor=valor, dia=dia))
            db.commit()
            enviar(chat_id, f"✅ *Salário Salvo!*\n💵 R$ {valor:,.2f}\n📅 Dia {dia}")
            return

        # Gasto por linguagem natural
        pagamento = "Dinheiro"
        if "pix" in texto_limpo:
            pagamento = "Pix"
        elif "debito" in texto_limpo or "débito" in texto_limpo:
            pagamento = "Débito"
        elif any(p in texto_limpo for p in ["credito", "crédito", "cartao", "cartão"]):
            pagamento = "Crédito"

        m_val = re.search(r'(\d+[\.,]\s?\d+|\d+)', texto_original)
        if m_val:
            val_txt   = m_val.group(1)
            valor     = float(val_txt.replace(" ", "").replace(",", "."))
            categoria = texto_original.replace(val_txt, "")
            for t in ["debito", "débito", "credito", "crédito", "pix", "dinheiro", "cartao", "cartão", "ifood"]:
                categoria = re.sub(t, "", categoria, flags=re.IGNORECASE)
            categoria = categoria.strip().capitalize() or "Outros"
            db.add(models.Gasto(valor=valor, categoria=categoria, forma_pagamento=pagamento))
            db.commit()
            enviar(chat_id, f"✅ *Salvo com Sucesso!*\n💰 R$ {valor:.2f}\n🏷️ {categoria}\n💳 {pagamento}")
        else:
            enviar(chat_id, "❓ Não encontrei o valor. Tente: `50 lanche cartao`")

    finally:
        db.close()


def _health_server():
    import os
    from http.server import BaseHTTPRequestHandler, HTTPServer
    port = int(os.getenv("PORT", 10000))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()
        def log_message(self, *args):
            pass  # silencia logs do servidor HTTP

    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


def _pegar_offset_inicial():
    """Descarta todas as mensagens pendentes e retorna o próximo offset."""
    try:
        r = requests.get(f"{BASE}/getUpdates", params={"offset": -1, "timeout": 0}, timeout=10)
        updates = r.json().get("result", [])
        if updates:
            return updates[-1]["update_id"] + 1
    except Exception:
        pass
    return 0


def main():
    import threading
    threading.Thread(target=_health_server, daemon=True).start()

    print("=" * 45)
    print("  Bot Financeiro — Modo Polling  v6")
    print("  Ctrl+C para parar")
    print("=" * 45)

    # Descarta mensagens acumuladas durante downtime/deploy
    offset = _pegar_offset_inicial()
    print(f"  Offset inicial: {offset}")

    while True:
        try:
            r = requests.get(
                f"{BASE}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=35
            )
            for upd in r.json().get("result", []):
                offset = upd["update_id"] + 1
                if "message" in upd:
                    try:
                        processar(upd["message"])
                    except Exception as e:
                        print(f"Erro ao processar mensagem: {e}")
        except requests.exceptions.Timeout:
            pass
        except Exception as e:
            print(f"Erro na conexão: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()
