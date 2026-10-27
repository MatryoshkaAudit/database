from datetime import datetime

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from matryoshka_db.db_models.base import Base, TimestampMixin, get_utc_now
from matryoshka_db.db_models.enum_models import ComplianceStatusEnum


class Certificate(Base, TimestampMixin):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    reg_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[ComplianceStatusEnum] = mapped_column(
        Enum(ComplianceStatusEnum), default=ComplianceStatusEnum.COMPLIANT
    )

    pp719_points: Mapped[int] = mapped_column(Integer, default=0)
    ad_valorem_pct: Mapped[float] = mapped_column(Float, default=0.0)
    defacto_localization_pct: Mapped[float] = mapped_column(Float, default=0.0)
    vulnerability_gap_pct: Mapped[float] = mapped_column(Float, default=0.0)

    certified_by: Mapped[str] = mapped_column(String(255), default="Минпромторг РФ / ТПП РФ")
    qr_verification_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    digital_signature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(default=get_utc_now)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="certificates")
