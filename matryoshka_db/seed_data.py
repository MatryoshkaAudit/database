import asyncio
import hashlib
import json
from datetime import datetime, timedelta

from matryoshka_db.database import db_manager
from matryoshka_db.db_models import (
    Product,
    Supplier,
    Component,
    Analog,
    PolicyRule,
    CountryRisk,
    Certificate,
    AuditLog,
    ComplianceStatusEnum,
    SanctionsStatusEnum,
    AuditActorTypeEnum,
)


def calc_cfi(criticality: float, risk: float, analog_avail: float) -> float:
    """Формула CFI = Criticality * Risk * (1 - AnalogAvail)"""
    return round(criticality * risk * (1.0 - analog_avail), 4)


async def seed_database():
    """Заполнение базы данных эталонным кейсом лесозаготовительного харвестера ЛХ-4"""
    await db_manager.init_db()
    async with db_manager.get_session() as session:
        # Проверка идемпотентности
        from sqlalchemy import select
        res = await session.execute(select(Product).limit(1))
        if res.scalar_one_or_none():
            print("✓ База данных уже содержит начальные данные (идемпотентно)")
            return

        # 1. Справочник страновых рисков
        country_risks = [
            CountryRisk(country_code="RU", country_name="Российская Федерация", risk_factor=0.0, is_unfriendly=False),
            CountryRisk(country_code="BY", country_name="Республика Беларусь", risk_factor=0.05, is_unfriendly=False),
            CountryRisk(country_code="CN", country_name="Китайская Народная Республика", risk_factor=0.30, is_unfriendly=False),
            CountryRisk(country_code="KZ", country_name="Республика Казахстан (Транзит)", risk_factor=0.45, is_unfriendly=False),
            CountryRisk(country_code="CH", country_name="Швейцария", risk_factor=0.95, is_unfriendly=True, sanctions_regime="EU Sanctions"),
            CountryRisk(country_code="DE", country_name="Германия", risk_factor=0.95, is_unfriendly=True, sanctions_regime="EU Package 14"),
            CountryRisk(country_code="US", country_name="Соединенные Штаты Америки", risk_factor=1.0, is_unfriendly=True, sanctions_regime="US OFAC SDN"),
            CountryRisk(country_code="DK", country_name="Дания", risk_factor=0.90, is_unfriendly=True, sanctions_regime="EU Sanctions"),
            CountryRisk(country_code="FR", country_name="Франция", risk_factor=0.95, is_unfriendly=True, sanctions_regime="EU Sanctions"),
        ]
        session.add_all(country_risks)

        # 2. Правила ПП РФ № 719
        rule_forestry = PolicyRule(
            standard_name="ПП РФ № 719",
            industry_code="28.3",
            industry_name="Машины для лесного хозяйства и заготовки древесины",
            min_points_required=70,
            min_ad_valorem_pct=50.0,
            effective_year=2026,
        )
        session.add(rule_forestry)

        # 3. Поставщики
        suppliers = [
            Supplier(name="ООО 'Лестехмаш'", inn="7701234567", country_code="RU", sanctions_status=SanctionsStatusEnum.CLEAN, reliability_rating=0.95),
            Supplier(name="ПАО 'Автодизель' (ЯМЗ)", inn="7601001234", country_code="RU", sanctions_status=SanctionsStatusEnum.CLEAN, reliability_rating=0.90),
            Supplier(name="АО 'Концерн НПО Аврора'", inn="7802345678", country_code="RU", sanctions_status=SanctionsStatusEnum.CLEAN, reliability_rating=0.92),
            Supplier(name="Silk Road Logistics (Алматы)", country_code="KZ", sanctions_status=SanctionsStatusEnum.WATCHLIST, reliability_rating=0.60, transit_jurisdictions="KZ,AE", notes="Канал серого и параллельного импорта"),
            Supplier(name="EuroHydraulics Export GmbH", country_code="DE", sanctions_status=SanctionsStatusEnum.EMBARGOED, reliability_rating=0.10, notes="Прямой запрет на отгрузки в РФ"),
            Supplier(name="АО 'ПКК Микрон'", inn="7735012345", country_code="RU", sanctions_status=SanctionsStatusEnum.CLEAN, reliability_rating=0.98, notes="Отечественный производитель интегральных микросхем"),
            Supplier(name="АО 'НИИЭТ'", inn="3662005432", country_code="RU", sanctions_status=SanctionsStatusEnum.CLEAN, reliability_rating=0.94, notes="Разработчик отечественных 32-разрядных микроконтроллеров"),
        ]
        session.add_all(suppliers)
        await session.flush()

        # 4. Продукт: Харвестер ЛХ-4
        product = Product(
            name="Харвестер гусеничный ЛХ-4 'Тайга'",
            article="LH-4-2026",
            category="Лесозаготовительная техника",
            target_industry="28.3",
            total_cost_rub=45000000.0,
            description="Лесосечная машина тяжелого класса для выборочных и сплошных рубок. Оборудована харвестерной головкой с измерительной системой диаметра ствола и длины кряжа.",
        )
        session.add(product)
        await session.flush()

        # 5. Иерархия BOM: Tier 1, Tier 2, Tier 3
        # TIER 1: Харвестерная головка H414 (Бумажная локализация РФ)
        head_t1 = Component(
            product_id=product.id,
            name="Харвестерная головка H414-RU",
            article="H414-RU-01",
            tier=1,
            hs_code="8436801000",
            country_code="RU",
            manufacturer="ООО 'Лестехмаш'",
            unit_cost_rub=12500000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.0,
            analog_availability=0.9,
            cfi_score=0.0,
            is_chokepoint=False,
            lead_time_days=45,
            notes="По документам проходит как 100% российское производство (сборка в Вологде).",
        )
        session.add(head_t1)
        await session.flush()

        # TIER 2 (под харвестерной головкой): Гидравлический пропорциональный блок
        valve_t2 = Component(
            product_id=product.id,
            parent_id=head_t1.id,
            name="Пропорциональный гидроблок PVG-32 Mod",
            article="PVG-32-RU",
            tier=2,
            hs_code="8481201009",
            country_code="RU",
            manufacturer="ООО 'Гидросила-Инжиниринг'",
            unit_cost_rub=3200000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.1,
            analog_availability=0.7,
            cfi_score=0.03,
            is_chokepoint=False,
            lead_time_days=60,
            notes="Корпус отлит в РФ, но электронная плата управления импортная.",
        )
        session.add(valve_t2)
        await session.flush()

        # TIER 3 (Chokepoint 1): Микроконтроллер клапана STM32F407 (Парадокс копеечного чипа!)
        stm32_t3 = Component(
            product_id=product.id,
            parent_id=valve_t2.id,
            name="Микроконтроллер ARM Cortex-M4 STM32F407VGT6",
            article="STM32F407VGT6",
            tier=3,
            hs_code="8542319010",
            country_code="CH",
            manufacturer="STMicroelectronics",
            unit_cost_rub=1850.0,
            quantity=4.0,
            criticality=1.0,
            country_risk=0.95,
            analog_availability=0.05, # Прямого пин-ту-пин аналога на складе нет
            cfi_score=calc_cfi(1.0, 0.95, 0.05), # 0.9025
            is_chokepoint=True,
            lead_time_days=180,
            notes="КРИТИЧЕСКИЙ УЗЕЛ! Без этого чипа за 1850 руб. гидроблок не работает, харвестерная головка не пилит лес. Поставка идет через серый транзит Казахстана.",
        )
        session.add(stm32_t3)

        # TIER 3 (Компонент 2): Датчик давления Danfoss MBS
        danfoss_t3 = Component(
            product_id=product.id,
            parent_id=valve_t2.id,
            name="Датчик давления MBS-3000 (0-400 bar)",
            article="MBS3000-060G",
            tier=3,
            hs_code="9026202000",
            country_code="DK",
            manufacturer="Danfoss A/S",
            unit_cost_rub=42000.0,
            quantity=6.0,
            criticality=0.9,
            country_risk=0.90,
            analog_availability=0.70, # Есть китайские и российские аналоги с переходником
            cfi_score=calc_cfi(0.9, 0.90, 0.70), # 0.243
            is_chokepoint=False,
            lead_time_days=90,
        )
        session.add(danfoss_t3)

        # TIER 1: Дизельный двигатель ЯМЗ-536
        engine_t1 = Component(
            product_id=product.id,
            name="Дизельный двигатель ЯМЗ-536-Лесник (312 л.с.)",
            article="YMZ-536-L",
            tier=1,
            hs_code="8408209907",
            country_code="RU",
            manufacturer="ПАО 'Автодизель'",
            unit_cost_rub=3800000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.0,
            analog_availability=0.95,
            cfi_score=0.0,
            is_chokepoint=False,
            lead_time_days=30,
        )
        session.add(engine_t1)
        await session.flush()

        # TIER 2: Топливная аппаратура Common Rail
        cr_t2 = Component(
            product_id=product.id,
            parent_id=engine_t1.id,
            name="Система впрыска Common Rail 1800 bar",
            article="CR-1800-YMZ",
            tier=2,
            hs_code="8413302008",
            country_code="RU",
            manufacturer="Ярославский завод дизельной аппаратуры",
            unit_cost_rub=1200000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.2,
            analog_availability=0.8,
            cfi_score=0.04,
            is_chokepoint=False,
            lead_time_days=45,
        )
        session.add(cr_t2)
        await session.flush()

        # TIER 3 (Chokepoint 2): Форсунки Bosch CRI
        bosch_t3 = Component(
            product_id=product.id,
            parent_id=cr_t2.id,
            name="Электромагнитная форсунка высокого давления CRI2",
            article="0445120153",
            tier=3,
            hs_code="8409990009",
            country_code="DE",
            manufacturer="Robert Bosch GmbH",
            unit_cost_rub=85000.0,
            quantity=6.0,
            criticality=1.0,
            country_risk=0.95,
            analog_availability=0.15,
            cfi_score=calc_cfi(1.0, 0.95, 0.15), # 0.8075
            is_chokepoint=True,
            lead_time_days=120,
            notes="КРИТИЧЕСКИЙ УЗЕЛ! 14-й пакет санкций перекрыл канал поставки через Турцию. Риск остановки двигателей.",
        )
        session.add(bosch_t3)

        # TIER 1: Бортовой компьютер и система учёта кругляка "Кедр-М"
        computer_t1 = Component(
            product_id=product.id,
            name="Бортовая система таксации и управления 'Кедр-М'",
            article="KEDR-M-SYS",
            tier=1,
            hs_code="8471410000",
            country_code="RU",
            manufacturer="АО 'Концерн НПО Аврора'",
            unit_cost_rub=1950000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.0,
            analog_availability=0.85,
            cfi_score=0.0,
            is_chokepoint=False,
            lead_time_days=30,
        )
        session.add(computer_t1)
        await session.flush()

        # TIER 2: Вычислительный модуль реального времени
        dsp_t2 = Component(
            product_id=product.id,
            parent_id=computer_t1.id,
            name="Плата быстродействующего сбора данных с энкодеров",
            article="DSP-BOARD-V3",
            tier=2,
            hs_code="8473302008",
            country_code="RU",
            manufacturer="ООО 'Северная Электроника'",
            unit_cost_rub=650000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.2,
            analog_availability=0.6,
            cfi_score=0.08,
            is_chokepoint=False,
            lead_time_days=45,
        )
        session.add(dsp_t2)
        await session.flush()

        # TIER 3 (Chokepoint 3): ПЛИС Xilinx Spartan-6 (США)
        xilinx_t3 = Component(
            product_id=product.id,
            parent_id=dsp_t2.id,
            name="ПЛИС FPGA Spartan-6 XC6SLX45-2CSG324I",
            article="XC6SLX45-2CSG324I",
            tier=3,
            hs_code="8542399010",
            country_code="US",
            manufacturer="AMD / Xilinx Inc.",
            unit_cost_rub=4500.0,
            quantity=2.0,
            criticality=1.0,
            country_risk=1.0,
            analog_availability=0.0, # Прямого пин-ту-пин аналога нет в мире кроме клонов
            cfi_score=calc_cfi(1.0, 1.0, 0.0), # 1.0 (Максимальный риск O-Ring!)
            is_chokepoint=True,
            lead_time_days=240,
            notes="АБСОЛЮТНЫЙ CHOKEPOINT (CFI = 1.0). Обрабатывает оптические датчики длины ствола. Запрет на экспорт из США.",
        )
        session.add(xilinx_t3)

        # TIER 1: Ходовая часть и кабина
        cabin_t1 = Component(
            product_id=product.id,
            name="Кабина оператора FOPS/ROPS с климат-контролем",
            article="CAB-TAIGA-4",
            tier=1,
            hs_code="8707909009",
            country_code="RU",
            manufacturer="ООО 'Лестехмаш'",
            unit_cost_rub=2100000.0,
            quantity=1.0,
            criticality=0.8,
            country_risk=0.0,
            analog_availability=1.0,
            cfi_score=0.0,
            is_chokepoint=False,
            lead_time_days=20,
        )
        chassis_t1 = Component(
            product_id=product.id,
            name="Гусеничное шасси высокой проходимости с гидростатикой",
            article="CHASSIS-H-800",
            tier=1,
            hs_code="8708709909",
            country_code="BY",
            manufacturer="ОАО 'Амкодор'",
            unit_cost_rub=6400000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.05,
            analog_availability=0.9,
            cfi_score=0.005,
            is_chokepoint=False,
            lead_time_days=40,
        )
        session.add_all([cabin_t1, chassis_t1])
        await session.flush()

        # 6. Каталог отечественных аналогов для устранения уязвимостей
        analogs = [
            Analog(
                component_id=stm32_t3.id,
                name="32-разрядный микроконтроллер MIK32 'Амур' (RISC-V)",
                manufacturer="АО 'ПКК Микрон'",
                country_code="RU",
                unit_cost_rub=2400.0,
                redesign_cost_rub=450000.0,
                lead_time_days=30,
                compatibility_score=0.75,
                description="Отечественный микроконтроллер на архитектуре RISC-V. Требует адаптации прошивки и разводки печатной платы, но полностью исключает риск вторичных санкций.",
            ),
            Analog(
                component_id=stm32_t3.id,
                name="Микроконтроллер К1921ВК01Т (ARM Cortex-M4F)",
                manufacturer="АО 'НИИЭТ' (Воронеж)",
                country_code="RU",
                unit_cost_rub=3100.0,
                redesign_cost_rub=350000.0,
                lead_time_days=45,
                compatibility_score=0.85,
                description="Аппаратно близкий аналог Cortex-M4. Периферия ШИМ для управления гидроклапанами на борту.",
            ),
            Analog(
                component_id=bosch_t3.id,
                name="Форсунка электроуправляемая АЗПИ F-002",
                manufacturer="ООО 'Алтайский завод прецизионных изделий' (АЗПИ)",
                country_code="RU",
                unit_cost_rub=62000.0,
                redesign_cost_rub=150000.0,
                lead_time_days=25,
                compatibility_score=0.90,
                description="Отечественная форсунка Common Rail, одобрена для двигателей ЯМЗ-536.",
            ),
        ]
        session.add_all(analogs)

        # 7. Официальный сертификат ПП РФ № 719 (демонстрация парадокса)
        cert = Certificate(
            product_id=product.id,
            reg_number="RU-МПТ-719/2026-08412",
            status=ComplianceStatusEnum.COMPLIANT,
            pp719_points=78, # Порог 70 - ПРОЙДЕНО!
            ad_valorem_pct=88.5, # Порог 50% - ПРОЙДЕНО!
            defacto_localization_pct=41.2, # Реальная локализация всего 41.2%!
            vulnerability_gap_pct=47.3, # Разрыв 47.3%
            certified_by="Департамент сельскохозяйственного, пищевого и строительно-дорожного машиностроения Минпромторга РФ",
            qr_verification_url="https://gisp.gov.ru/pp719/cert/RU-MPT-719-2026-08412",
            digital_signature_hash=hashlib.sha256(b"MINPROMTORG_STAMP_RU_719_2026").hexdigest(),
            expires_at=datetime.utcnow() + timedelta(days=365),
        )
        session.add(cert)

        # 8. Журнал аудита (первоначальная запись)
        audit_event = AuditLog(
            event_type="SYSTEM_INITIAL_AUDIT",
            actor_id=1,
            actor_role=AuditActorTypeEnum.REGULATOR,
            resource_type="product",
            resource_id=product.id,
            details={
                "action": "BOM_STRESS_AUDIT",
                "summary": "Обнаружено 3 критических chokepoint-узла (STM32, Bosch CRI, Xilinx Spartan-6)",
                "paper_loc": 88.5,
                "defacto_loc": 41.2,
                "o_ring_paralysis_risk": 0.95,
            },
            hash_sha256=hashlib.sha256(b"INITIAL_SEED_AUDIT_TRANSACTION").hexdigest(),
        )
        session.add(audit_event)

        await session.commit()
        print("✓ База данных MatryoshkaAudit успешно заполнена эталонными данными Харвестера ЛХ-4!")


if __name__ == "__main__":
    asyncio.run(seed_database())
