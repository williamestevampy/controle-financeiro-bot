import os
import re
import requests
import models
from fastapi import FastAPI, Request, Depends
from database import SessionLocal, engine
from sqlalchemy.orm import Session
from sqlalchemy import desc
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (.env)
load_dotenv()

# Cria as tabelas no banco de dados automaticamente
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Obtém o Token do Telegram de forma segura
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

@app.post("/webhook")
async def receber_mensagem(request: Request, db: Session = Depends(get_db)):
    dados = await request.json()
    
    if "message" in dados and "text" in dados["message"]:
        texto_original = dados["message"]["text"]
        texto_limpo = texto_original.lower()
        chat_id = dados["message"]["chat"]["id"]
        
        # Comandos de sistema
        if texto_limpo == "/start":
            enviar_mensagem(chat_id, "🚀 **Bot Financeiro Pro Ativo!**\n\nEnvie: `40,88 mercado credito` ou `15 lanche pix`.")
            return {"status": "ok"}

        if texto_limpo == "/extrato":
            gastos = db.query(models.Gasto).order_by(desc(models.Gasto.data_hora)).limit(10).all()
            if not gastos:
                enviar_mensagem(chat_id, "Nenhum gasto registrado.")
            else:
                msg = "📋 **Últimos 10 Gastos**\n\n"
                for g in gastos:
                    msg += f"• {g.data_hora.strftime('%d/%m')} - {g.categoria}: *R$ {g.valor:.2f}* ({g.forma_pagamento})\n"
                enviar_mensagem(chat_id, msg)
            return {"status": "ok"}

        # 1. Identificação robusta da forma de pagamento (com e sem acento)
        pagamento = "Dinheiro"
        if "pix" in texto_limpo: 
            pagamento = "Pix"
        elif "debito" in texto_limpo or "débito" in texto_limpo: 
            pagamento = "Débito"
        elif any(p in texto_limpo for p in ["credito", "crédito", "cartao", "cartão"]): 
            pagamento = "Crédito"

        # 2. Busca o valor numérico (Regex para aceitar vários formatos de espaço e vírgula)
        busca_valor = re.search(r'(\d+[\.,]\s?\d+|\d+)', texto_original)
        
        if busca_valor:
            valor_texto = busca_valor.group(1)
            valor_limpo = valor_texto.replace(" ", "").replace(",", ".")
            valor = float(valor_limpo)
            
            # 3. Limpeza da categoria: remove valor e palavras-chave de pagamento
            categoria = texto_original.replace(valor_texto, "")
            termos_remover = [
                "debito", "débito", "credito", "crédito", 
                "pix", "dinheiro", "cartao", "cartão", "ifood"
            ]
            for t in termos_remover:
                categoria = re.sub(t, "", categoria, flags=re.IGNORECASE)
            
            categoria = categoria.strip().capitalize()
            if not categoria: categoria = "Outros"

            # 4. Salva no Banco de Dados Cloud (Aiven)
            novo_gasto = models.Gasto(valor=valor, categoria=categoria, forma_pagamento=pagamento)
            db.add(novo_gasto)
            db.commit()
            
            enviar_mensagem(chat_id, f"✅ **Salvo com Sucesso!**\n💰 R$ {valor:.2f}\n🏷️ {categoria}\n💳 {pagamento}")
        else:
            enviar_mensagem(chat_id, "❓ Não encontrei o valor. Tente algo como: `50.00 lanche cartao`.")

    return {"status": "ok"}