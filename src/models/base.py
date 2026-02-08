from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Trend(Base):
    __tablename__ = 'trends'
    
    id = Column(Integer, primary_key=True)
    niche = Column(String(50), index=True)  # 'Cinema', 'Sport', 'Music'
    topic = Column(String(255), unique=True, index=True) # Ex: "Trailer GTA 6", "Mbappé"
    first_detected = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relation One-to-Many vers les métriques
    metrics = relationship("TrendMetric", back_populates="trend")

class TrendMetric(Base):
    """Stocke l'évolution de la viralité à chaque scan (Time Series)"""
    __tablename__ = 'trend_metrics'
    
    id = Column(Integer, primary_key=True)
    trend_id = Column(Integer, ForeignKey('trends.id'))
    platform = Column(String(50)) # 'Google', 'TikTok', 'X'
    volume = Column(Integer) # Nombre de recherches/vues
    velocity_score = Column(Float) # Notre algo de viralité
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    trend = relationship("Trend", back_populates="metrics")

# Configuration DB (On utilisera SQLite pour le dev local, facile à passer en Postgres)
engine = create_engine('sqlite:///viral_data.db') 
Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)