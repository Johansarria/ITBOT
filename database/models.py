# database/models.py

from sqlalchemy import Column, String, Numeric, TIMESTAMP, BOOLEAN, BIGINT, text, TEXT, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Operations(Base):
    __tablename__ = 'operations'

    operation_id = Column(String(255), primary_key=True)
    timestamp = Column(TIMESTAMP, nullable=False)
    symbol = Column(String(255), nullable=False)
    side = Column(String(255), nullable=False)
    price = Column(Numeric, nullable=False)
    quantity = Column(Numeric, nullable=False)
    status = Column(String(255), nullable=False)
    mode = Column(String(255), nullable=False)
    decision = Column(String(255))
    escudo = Column(String(255))
    riesgo_forzado_activo = Column(BOOLEAN)
    ganancia_pct_operacion = Column(Numeric)
    close_price = Column(Numeric)
    close_timestamp = Column(TIMESTAMP)
    close_reason = Column(String(255))

class Klines(Base):
    __tablename__ = 'klines'

    timestamp = Column(BIGINT, primary_key=True)
    symbol = Column(String(255), primary_key=True)
    interval = Column(String(255), primary_key=True)
    open = Column(Numeric, nullable=False)
    high = Column(Numeric, nullable=False)
    low = Column(Numeric, nullable=False)
    close = Column(Numeric, nullable=False)
    volume = Column(Numeric, nullable=False)
    close_time = Column(BIGINT, nullable=False)

class DiscardedSignals(Base):
    __tablename__ = 'discarded_signals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP, nullable=False)
    strategy = Column(String(255), nullable=False)
    symbol = Column(String(255), nullable=False)
    interval = Column(String(255), nullable=False)
    decision = Column(String(255), nullable=False)
    score = Column(Numeric)
    features = Column(TEXT)
