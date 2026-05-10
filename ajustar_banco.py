from sqlalchemy import text
from database import engine

# O comando que "abre a gaveta" nova no banco de dados
sql_comando = text("ALTER TABLE gastos ADD COLUMN forma_pagamento VARCHAR(50) DEFAULT 'Dinheiro';")

print("⏳ Tentando adicionar a coluna 'forma_pagamento'...")

try:
    with engine.connect() as conexao:
        conexao.execute(sql_comando)
        conexao.commit() # Salva a alteração
        print("✅ Sucesso! A coluna foi criada.")
except Exception as e:
    # Se a coluna já existir, ele vai dar um erro avisando, o que é normal
    print(f"⚠️ Aviso ou Erro: {e}")

print("🚀 Agora você já pode rodar o seu Robô atualizado!")