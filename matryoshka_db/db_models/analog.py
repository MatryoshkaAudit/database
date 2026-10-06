from sqlalchemy import String, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from matryoshka_db.db_models.base import Base, TimestampMixin


class Analog(Base, TimestampMixin):
    __tablename__ = "analogs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(255), default="")
    country_code: Mapped[str] = mapped_column(String(3), default="RU")
    unit_cost_rub: Mapped[float] = mapped_column(Float, default=0.0)
    redesign_cost_rub: Mapped[float] = mapped_column(Float, default=0.0) # Затраты на адаптацию схемотехники
    lead_time_days: Mapped[int] = mapped_column(Integer, default=30)
    compatibility_score: Mapped[float] = mapped_column(Float, default=1.0) # 1.0 (drop-in) или 0.7 (нужна плата)
    compatibility_status: Mapped[str] = mapped_column(String(50), default="FULL_COMPATIBLE")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    component: Mapped["Component"] = relationship("Component", back_populates="analogs")
