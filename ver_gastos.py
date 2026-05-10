from database import SessionLocal
import models

# 1. Abre a conexão com o banco na nuvem
db = SessionLocal()

print("\n--- LISTA DE GASTOS NO BANCO ---")

try:
    # 2. Busca todos os gastos salvos
    gastos = db.query(models.Gasto).all()

    if not gastos:
        print("O banco ainda está vazio. Mande algo para o bot!")
    else:
        # 3. Exibe cada um de forma organizada
        for g in gastos:
            data_formatada = g.data_hora.strftime("%d/%m/%Y %H:%M")
            print(f"ID: {g.id} | Data: {data_formatada} | Categoria: {g.categoria} | Valor: R$ {g.valor:.2f}")

except Exception as e:
    print(f"Erro ao buscar dados: {e}")

finally:
    # 4. Fecha a conexão
    db.close()
print("--------------------------------\n")