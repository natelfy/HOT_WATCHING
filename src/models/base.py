import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timedelta

Base = declarative_base()

# ─── ABSOLUTE DB PATH ───────────────────────────────────────────────
# Cron runs from / so relative paths break. Always use absolute.
DB_DIR = os.environ.get("VIRAL_DB_DIR", "/app")
DB_PATH = os.path.join(DB_DIR, "viral_data.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"


class Trend(Base):
    __tablename__ = 'trends'

    id = Column(Integer, primary_key=True)
    niche = Column(String(50), index=True)          # 'Cinema', 'Sport', 'Music', 'General'
    topic = Column(String(255), unique=True, index=True)
    source_platform = Column(String(50))              # Platform where first detected
    first_detected = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    metrics = relationship("TrendMetric", back_populates="trend", cascade="all, delete-orphan")


class TrendMetric(Base):
    """Time-series: one row per (trend, platform, scan_window).
    The UniqueConstraint prevents duplicate metrics for the same trend+platform
    within the same 4-hour scan window."""
    __tablename__ = 'trend_metrics'

    id = Column(Integer, primary_key=True)
    trend_id = Column(Integer, ForeignKey('trends.id'), nullable=False)
    platform = Column(String(50), nullable=False)
    volume = Column(Integer, default=0)
    velocity_score = Column(Float, default=0.0)
    scan_window = Column(String(20))                  # e.g. "2025-02-08_12" (date_hour block)
    timestamp = Column(DateTime, default=datetime.utcnow)

    trend = relationship("Trend", back_populates="metrics")

    __table_args__ = (
        UniqueConstraint('trend_id', 'platform', 'scan_window', name='uq_trend_platform_window'),
    )


# ─── ENGINE & SESSION ───────────────────────────────────────────────
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(engine)
    print(f"✅ DB initialisée : {DB_PATH}")


def get_scan_window() -> str:
    """Returns a string like '2025-02-08_12' representing the current 4h block.
    Used to deduplicate metrics within the same scan cycle."""
    now = datetime.utcnow()
    block = (now.hour // 4) * 4
    return now.strftime(f"%Y-%m-%d_{block:02d}")


def upsert_trend(session, topic: str, niche: str, platform: str) -> Trend:
    """Get-or-create a Trend. Updates last_updated if it already exists."""
    trend = session.query(Trend).filter_by(topic=topic).first()
    if not trend:
        trend = Trend(topic=topic, niche=niche, source_platform=platform)
        session.add(trend)
        session.flush()  # get the ID without full commit
    else:
        trend.last_updated = datetime.utcnow()
    return trend


def add_metric(session, trend: Trend, platform: str, volume: int, velocity_score: float):
    """Insert a metric, skipping duplicates for the same scan window."""
    window = get_scan_window()

    existing = session.query(TrendMetric).filter_by(
        trend_id=trend.id, platform=platform, scan_window=window
    ).first()

    if existing:
        # Update if new data is better
        if volume > existing.volume:
            existing.volume = volume
            existing.velocity_score = velocity_score
        return existing

    metric = TrendMetric(
        trend_id=trend.id,
        platform=platform,
        volume=volume,
        velocity_score=velocity_score,
        scan_window=window,
    )
    session.add(metric)
    return metric