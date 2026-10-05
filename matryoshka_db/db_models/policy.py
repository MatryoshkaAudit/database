from sqlalchemy import String, Float, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from matryoshka_db.db_models.base import Base, TimestampMixin


class PolicyRule(Base, TimestampMixin):
    __tablename__ = "policy_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    standard_name: Mapped[str] = mapped_column(String(100), default="ПП РФ № 719")
    industry_code: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "28.3"
    industry_name: Mapped[str] = mapped_column(String(255), default="Машиностроение для лесозаготовительной отрасли")
    min_points_required: Mapped[int] = mapped_column(Integer, default=70) # Порог баллов (например 70 для 2026 г.)
    min_ad_valorem_pct: Mapped[float] = mapped_column(Float, default=50.0) # Порог адвалорной доли (50%)
    effective_year: Mapped[int] = mapped_column(Integer, default=2026)


class CountryRisk(Base, TimestampMixin):
    __tablename__ = "country_risks"

    country_code: Mapped[str] = mapped_column(String(3), primary_key=True) # "RU", "CN", "US", "DE"
    country_name: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_factor: Mapped[float] = mapped_column(Float, default=0.0) # 0.0 - 1.0
    is_unfriendly: Mapped[bool] = mapped_column(Boolean, default=False)
    sanctions_regime: Mapped[str | None] = mapped_column(String(255), nullable=True) # "EU Package 14, US OFAC"
