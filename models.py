from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime, timezone, timedelta
from database import Base

_BR = timezone(timedelta(hours=-3))

def _now_br():
    return datetime.now(_BR).replace(tzinfo=None)

class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    valor = Column(Float, nullable=False)
    categoria = Column(String(100), nullable=False)
    forma_pagamento = Column(String(50), default="Dinheiro")
    data_hora = Column(DateTime, default=_now_br)

class Provento(Base):
    __tablename__ = "proventos"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(150), nullable=False)
    valor = Column(Float, nullable=False)
    dia = Column(Integer, nullable=True)
    data_hora = Column(DateTime, default=_now_br)

class UpdateProcessado(Base):
    __tablename__ = "updates_processados"

    update_id = Column(Integer, primary_key=True)
    processado_em = Column(DateTime, default=_now_br)