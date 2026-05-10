from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base

class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    valor = Column(Float, nullable=False)
    categoria = Column(String(100), nullable=False)
    forma_pagamento = Column(String(50), default="Dinheiro") # <-- ESTA LINHA É OBRIGATÓRIA
    data_hora = Column(DateTime, default=datetime.now)