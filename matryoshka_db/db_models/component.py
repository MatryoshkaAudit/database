from sqlalchemy import String, Float, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from matryoshka_db.db_models.base import Base, TimestampMixin


class Component(Base, TimestampMixin):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    article: Mapped[str] = mapped_column(String(100), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, default=1) # 1, 2, 3
    hs_code: Mapped[str] = mapped_column(String(20), default="") # Код ТН ВЭД

    country_code: Mapped[str] = mapped_column(String(3), default="RU")
    manufacturer: Mapped[str] = mapped_column(String(255), default="")
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)

    unit_cost_rub: Mapped[float] = mapped_column(Float, default=0.0)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)

    # Метрики риска и O-Ring
    criticality: Mapped[float] = mapped_column(Float, default=1.0) # 0.0 .. 1.0 (важность узла для работы машины)
    country_risk: Mapped[float] = mapped_column(Float, default=0.0) # 0.0 (РФ) .. 1.0 (ЕС/США)
    analog_availability: Mapped[float] = mapped_column(Float, default=1.0) # 1.0 (drop-in) .. 0.0 (нет)
    
    # Статус наличия аналогов:
    # "FULL_COMPATIBLE" (Совместим полностью), "REQUIRES_REWORK" (Требует доработки),
    # "POORLY_COMPATIBLE" (Практически несовместим), "NO_ANALOGS" (Аналоги отсутствуют)
    analog_status: Mapped[str] = mapped_column(String(50), default="NO_ANALOGS")

    # Critical Failure Index = Criticality * Risk * (1 - AnalogAvail)
    cfi_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_chokepoint: Mapped[bool] = mapped_column(Boolean, default=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=14)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="components")
    supplier: Mapped["Supplier | None"] = relationship("Supplier", back_populates="components")
    parent: Mapped["Component | None"] = relationship("Component", remote_side=[id], back_populates="children")
    children: Mapped[list["Component"]] = relationship("Component", back_populates="parent", cascade="all, delete-orphan")
    analogs: Mapped[list["Analog"]] = relationship("Analog", back_populates="component", cascade="all, delete-orphan")
