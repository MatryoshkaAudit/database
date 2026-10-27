from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from matryoshka_db.db_models.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    article: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="Лесозаготовительная техника")
    target_industry: Mapped[str] = mapped_column(String(100), default="28.3 Лесозаготовительное машиностроение")
    enterprise_name: Mapped[str] = mapped_column(String(255), default="АО «Лестехмаш»")
    enterprise_inn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    enterprise_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    total_cost_rub: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Статус стратегической важности для Минпромторга РФ и ИИ-аудита
    is_strategic: Mapped[bool] = mapped_column(Boolean, default=False)
    strategic_priority: Mapped[str] = mapped_column(String(50), default="NORMAL")  # "CRITICAL", "HIGH", "NORMAL"
    strategic_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    components: Mapped[list["Component"]] = relationship(
        "Component", back_populates="product", cascade="all, delete-orphan"
    )
    certificates: Mapped[list["Certificate"]] = relationship("Certificate", back_populates="product")
