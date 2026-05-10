from sqlalchemy import text
from database import engine

# O comando TRUNCATE apaga todos os dados e reinicia a contagem de IDs
sql_comando = text("TRUNCATE TABLE gastos;")

print("⚠️ Preparando para apagar todos os registros...")

# Pergunta de confirmação no terminal para evitar acidentes
confirmacao = input("Tem certeza que deseja ZERAR o banco de dados? (s/n): ")

if confirmacao.lower() == 's':
    try:
        with engine.connect() as conexao:
            conexao.execute(sql_comando)
            conexao.commit()
            print("✅ Banco de dados zerado com sucesso! Pronto para recomeçar.")
    except Exception as e:
        print(f"❌ Erro ao limpar o banco: {e}")
else:
    print("❌ Operação cancelada. Seus dados continuam salvos.")