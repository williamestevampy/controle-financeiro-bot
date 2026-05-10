import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Obtém a URL do banco de dados das variáveis de ambiente
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Configuração do Engine com suporte a SSL para o Aiven
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"ssl": {"ca": None}}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()