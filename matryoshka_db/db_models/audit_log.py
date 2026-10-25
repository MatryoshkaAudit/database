from sqlalchemy import JSON, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from matryoshka_db.db_models.base import Base, TimestampMixin
from matryoshka_db.db_models.enum_models import AuditActorTypeEnum


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_role: Mapped[AuditActorTypeEnum] = mapped_column(
        Enum(AuditActorTypeEnum), default=AuditActorTypeEnum.ENTERPRISE
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
