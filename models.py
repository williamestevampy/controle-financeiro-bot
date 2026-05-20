from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base

class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    valor = Column(Float, nullable=False)
    categoria = Column(String(100), nullable=False)
    forma_pagamento = Column(String(50), default="Dinheiro")
    data_hora = Column(DateTime, default=datetime.now)

class Provento(Base):
    __tablename__ = "proventos"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(150), nullable=False)
    valor = Column(Float, nullable=False)
    dia = Column(Integer, nullable=True)
    data_hora = Column(DateTime, default=datetime.now)