from enum import Enum, IntEnum


class TierLevelEnum(IntEnum):
    TIER_0 = 0  # Конечное готовое изделие (Харвестер ЛХ-4)
    TIER_1 = 1  # Крупные узлы первого уровня (Харвестерная головка, Двигатель, Кабина)
    TIER_2 = 2  # Подузлы и агрегаты (Гидроблок PVG, Топливный насос, Контроллер)
    TIER_3 = 3  # Компонентный базис (Микросхемы, датчики, уплотнения, форсунки)


class SanctionsStatusEnum(str, Enum):
    CLEAN = "clean"
    WATCHLIST = "watchlist"
    BLOCKED = "blocked"
    EMBARGOED = "embargoed"


class CountryRiskEnum(str, Enum):
    LOW = "low"  # РФ, Беларусь, ЕАЭС (Риск: 0.0 - 0.1)
    MEDIUM = "medium"  # Дружественные страны / нейтральные (Китай, Турция, Индия) (0.3 - 0.5)
    HIGH = "high"  # Санкционные страны ЕС/G7 (0.9 - 1.0)
    CRITICAL = "critical"  # Прямой запрет на экспорт технологий (1.0)


class AuditActorTypeEnum(str, Enum):
    ENTERPRISE = "enterprise"
    REGULATOR = "regulator"
    AUDITOR = "auditor"
    SYSTEM = "system"


class ComplianceStatusEnum(str, Enum):
    COMPLIANT = "compliant"
    CONDITIONAL = "conditional"
    NON_COMPLIANT = "non_compliant"
    CHOKEPOINT_RISK = "chokepoint_risk"
