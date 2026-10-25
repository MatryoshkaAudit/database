from sqlalchemy import Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from matryoshka_db.db_models.base import Base, TimestampMixin
from matryoshka_db.db_models.enum_models import SanctionsStatusEnum


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    inn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country_code: Mapped[str] = mapped_column(String(3), default="RU")
    sanctions_status: Mapped[SanctionsStatusEnum] = mapped_column(
        Enum(SanctionsStatusEnum), default=SanctionsStatusEnum.CLEAN
    )
    reliability_rating: Mapped[float] = mapped_column(Float, default=1.0)
    transit_jurisdictions: Mapped[str | None] = mapped_column(String(255), nullable=True) # e.g. "KZ,AE"
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    components: Mapped[list["Component"]] = relationship("Component", back_populates="supplier")
