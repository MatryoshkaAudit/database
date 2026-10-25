import hashlib
import secrets

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from matryoshka_db.db_models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Пользователь системы Матрёшка.Аудит (Завод или Минпромторг РФ)"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Роли: 'enterprise_engineer' (Завод) | 'regulator_admin' (Минпромторг РФ)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="enterprise_engineer", index=True)

    organization: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=True)
    inn: Mapped[str] = mapped_column(String(12), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @classmethod
    def create_with_password(
        cls,
        email: str,
        password: str,
        full_name: str,
        role: str,
        organization: str,
        department: str | None = None,
        inn: str | None = None,
    ) -> "User":
        salt = secrets.token_hex(16)
        hash_val = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
        return cls(
            email=email,
            password_hash=hash_val,
            password_salt=salt,
            full_name=full_name,
            role=role,
            organization=organization,
            department=department,
            inn=inn,
            is_active=True,
        )

    def verify_password(self, password: str) -> bool:
        check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), self.password_salt.encode("utf-8"), 100_000).hex()
        return secrets.compare_digest(self.password_hash, check)
