# 🤖 Controle Financeiro Bot & Dashboard

Um sistema completo de controle financeiro pessoal e familiar. O usuário registra seus gastos de forma rápida através de um Bot no Telegram, e os dados são processados e exibidos em tempo real em um Dashboard interativo na web.

## 🚀 Funcionalidades

* **Registro Fácil via Telegram:** Envie mensagens simples como `50,90 lanche cartao` e o bot interpreta o valor, a categoria e a forma de pagamento automaticamente.
* **Inteligência de Texto (Regex):** O bot lida com erros de digitação, espaços extras e acentuação de forma automática.
* **Dashboard Interativo:** Painel web construído com Streamlit, contendo gráficos de rosca e barras (Plotly) para análise de gastos por categoria e forma de pagamento.
* **Armazenamento em Nuvem:** Dados salvos de forma segura em um banco MySQL hospedado na Aiven.
* **Extrato Rápido:** Comando `/extrato` direto no Telegram para ver os últimos 10 gastos.

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3
* **Interface Conversacional:** API do Telegram
* **Backend do Bot:** FastAPI & Uvicorn
* **Painel Web (Dashboard):** Streamlit & Plotly
* **Banco de Dados:** MySQL (Aiven) & SQLAlchemy (ORM)
* **Controle de Variáveis:** python-dotenv

## ⚙️ Como rodar o projeto localmente

1. Clone o repositório:
   ```bash
   git clone [https://github.com/SEU_USUARIO/controle-financeiro-bot.git](https://github.com/SEU_USUARIO/controle-financeiro-bot.git)