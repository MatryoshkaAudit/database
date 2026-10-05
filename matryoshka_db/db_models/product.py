from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from matryoshka_db.db_models.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    article: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="Лесозаготовительная техника")
    target_industry: Mapped[str] = mapped_column(String(50), default="28.3")
    total_cost_rub: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    components: Mapped[list["Component"]] = relationship("Component", back_populates="product", cascade="all, delete-orphan")
    certificates: Mapped[list["Certificate"]] = relationship("Certificate", back_populates="product")
