import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone

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
    User,
    ComplianceStatusEnum,
    SanctionsStatusEnum,
    AuditActorTypeEnum,
)


def calc_cfi(criticality: float, risk: float, analog_avail: float) -> float:
    """Формула CFI = Criticality * Risk * (1 - AnalogAvail)"""
    return round(criticality * risk * (1.0 - analog_avail), 4)


async def seed_users(session):
    from sqlalchemy import select
    res = await session.execute(select(User).limit(1))
    if not res.scalar_one_or_none():
        users = [
            User.create_with_password(
                email="engineer@lestechmash.ru",
                password="Password123!",
                full_name="Смирнов Алексей Петрович",
                role="enterprise_engineer",
                organization="АО «Лестехмаш»",
                department="Отдел Главного Конструктора",
                inn="3525184920",
            ),
            User.create_with_password(
                email="engineer@stankomash.ru",
                password="Password123!",
                full_name="Ковалев Дмитрий Сергеевич",
                role="enterprise_engineer",
                organization="АО «Станкомаш-Холдинг»",
                department="Конструкторское бюро станкостроения",
                inn="3702654120",
            ),
            User.create_with_password(
                email="inspector@minpromtorg.gov.ru",
                password="Password123!",
                full_name="Лесных Иван Сергеевич",
                role="regulator_admin",
                organization="Минпромторг РФ",
                department="Ситуационный Центр ДСПСДМ",
                inn="7705596339",
            ),
        ]
        session.add_all(users)
        await session.commit()
        print("✓ Учётные записи Заводов и Минпромторга РФ успешно созданы!")


async def seed_database():
    """Заполнение базы данных эталонными промышленными кейсами и справочниками рисков"""
    await db_manager.init_db()
    async with db_manager.get_session() as session:
        await seed_users(session)

        # Проверка наличия продуктов
        from sqlalchemy import select
        res = await session.execute(select(Product).limit(1))
        if res.scalar_one_or_none():
            print("✓ База данных уже содержит начальные данные (идемпотентно)")
            return

        # 1. Государственный справочник страновых рисков (Минпромторг РФ)
        country_risks = [
            CountryRisk(country_code="RU", country_name="Российская Федерация", risk_factor=0.0, is_unfriendly=False),
            CountryRisk(country_code="BY", country_name="Республика Беларусь (Союзное гос-во)", risk_factor=0.0, is_unfriendly=False),
            CountryRisk(country_code="KZ", country_name="Республика Казахстан (ЕАЭС / Транзит)", risk_factor=0.35, is_unfriendly=False),
            CountryRisk(country_code="CN", country_name="Китайская Народная Республика (КНР)", risk_factor=0.25, is_unfriendly=False),
            CountryRisk(country_code="IN", country_name="Республика Индия", risk_factor=0.25, is_unfriendly=False),
            CountryRisk(country_code="TR", country_name="Турецкая Республика (Транзитный хаб)", risk_factor=0.50, is_unfriendly=False),
            CountryRisk(country_code="AE", country_name="Объединенные Арабские Эмираты (ОАЭ)", risk_factor=0.50, is_unfriendly=False),
            CountryRisk(country_code="CH", country_name="Швейцарская Конфедерация", risk_factor=0.95, is_unfriendly=True, sanctions_regime="EU Sanctions"),
            CountryRisk(country_code="DE", country_name="Федеративная Республика Германия", risk_factor=0.95, is_unfriendly=True, sanctions_regime="EU Package 14"),
            CountryRisk(country_code="US", country_name="Соединенные Штаты Америки", risk_factor=1.0, is_unfriendly=True, sanctions_regime="US OFAC / BIS SDN"),
            CountryRisk(country_code="DK", country_name="Королевство Дания", risk_factor=0.90, is_unfriendly=True, sanctions_regime="EU Sanctions"),
            CountryRisk(country_code="FR", country_name="Французская Республика", risk_factor=0.95, is_unfriendly=True, sanctions_regime="EU Sanctions"),
            CountryRisk(country_code="TW", country_name="Тайвань (TSMC / Полупроводники)", risk_factor=0.95, is_unfriendly=True, sanctions_regime="US Export Control"),
            CountryRisk(country_code="JP", country_name="Япония", risk_factor=0.95, is_unfriendly=True, sanctions_regime="METI Export Control"),
            CountryRisk(country_code="IT", country_name="Итальянская Республика", risk_factor=0.90, is_unfriendly=True, sanctions_regime="EU Sanctions"),
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
        rule_machinery = PolicyRule(
            standard_name="ПП РФ № 719",
            industry_code="28.4",
            industry_name="Станкоинструментальная промышленность и робототехника",
            min_points_required=75,
            min_ad_valorem_pct=55.0,
            effective_year=2026,
        )
        session.add_all([rule_forestry, rule_machinery])

        # 3. Поставщики
        suppliers = [
            Supplier(name="ООО 'Лестехмаш'", inn="3525184920", country_code="RU", sanctions_status=SanctionsStatusEnum.CLEAN, reliability_rating=0.95),
            Supplier(name="ПАО 'Автодизель' (ЯМЗ)", inn="7601001234", country_code="RU", sanctions_status=SanctionsStatusEnum.CLEAN, reliability_rating=0.90),
            Supplier(name="АО 'Концерн НПО Аврора'", inn="7802345678", country_code="RU", sanctions_status=SanctionsStatusEnum.CLEAN, reliability_rating=0.92),
            Supplier(name="Silk Road Logistics (Алматы)", country_code="KZ", sanctions_status=SanctionsStatusEnum.WATCHLIST, reliability_rating=0.60, transit_jurisdictions="KZ,AE", notes="Канал серого и параллельного импорта"),
            Supplier(name="EuroHydraulics Export GmbH", country_code="DE", sanctions_status=SanctionsStatusEnum.EMBARGOED, reliability_rating=0.10, notes="Прямой запрет на отгрузки в РФ"),
            Supplier(name="АО 'ПКК Микрон'", inn="7735012345", country_code="RU", sanctions_status=SanctionsStatusEnum.CLEAN, reliability_rating=0.98, notes="Отечественный производитель интегральных микросхем"),
            Supplier(name="АО 'НИИЭТ'", inn="3662005432", country_code="RU", sanctions_status=SanctionsStatusEnum.CLEAN, reliability_rating=0.94, notes="Разработчик отечественных 32-разрядных микроконтроллеров"),
            Supplier(name="ООО 'АЗПИ'", inn="2224010011", country_code="RU", sanctions_status=SanctionsStatusEnum.CLEAN, reliability_rating=0.95, notes="Алтайский завод прецизионных изделий"),
        ]
        session.add_all(suppliers)
        await session.flush()

        # =========================================================================
        # ПРОДУКТ 1: Харвестер ЛХ-4 «Тайга» (СТРАТЕГИЧЕСКИЙ ОБЪЕКТ ЛЕСТЕХА)
        # =========================================================================
        p1 = Product(
            name="Харвестер гусеничный ЛХ-4 «Тайга»",
            article="LH-4-2026",
            category="Лесозаготовительная техника",
            target_industry="28.3 Лесозаготовительное машиностроение",
            enterprise_name="АО «Лестехмаш»",
            enterprise_inn="3525184920",
            enterprise_city="г. Вологда",
            total_cost_rub=45000000.0,
            is_strategic=True,
            strategic_priority="CRITICAL",
            strategic_notes="Критически важное предприятие для лесопромышленного комплекса и инженерных частей РФ. Включено в перечень первоочередной господдержки.",
            description="Тяжелая лесосечная машина для выборочных и сплошных рубок. По документам имеет 88.5% локализации, но на 3-м уровне содержит микроконтроллер STM32 и форсунки Bosch.",
        )
        session.add(p1)
        await session.flush()

        # Tier 1 - Харвестерная головка H414
        h1_t1 = Component(
            product_id=p1.id,
            name="Харвестерная головка H414-RU",
            article="H414-RU-01",
            tier=1,
            hs_code="8436801000",
            country_code="RU",
            manufacturer="АО «Лестехмаш»",
            unit_cost_rub=12500000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.0,
            analog_availability=0.9,
            analog_status="FULL_COMPATIBLE",
            cfi_score=0.0,
            is_chokepoint=False,
            lead_time_days=45,
            notes="Отечественная сборка, сварка рамы и окраска в Вологде. Де-юре 85 баллов.",
        )
        session.add(h1_t1)
        await session.flush()

        # Tier 2 - Гидроблок
        valve_t2 = Component(
            product_id=p1.id,
            parent_id=h1_t1.id,
            name="Пропорциональный гидроблок PVG-32 Mod",
            article="PVG-32-RU",
            tier=2,
            hs_code="8481201009",
            country_code="RU",
            manufacturer="ООО «Гидросила-Инжиниринг»",
            unit_cost_rub=3200000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.1,
            analog_availability=0.7,
            analog_status="REQUIRES_REWORK",
            cfi_score=0.03,
            is_chokepoint=False,
            lead_time_days=60,
            notes="Корпус отлит в РФ, но электронная плата управления импортная.",
        )
        session.add(valve_t2)
        await session.flush()

        # Tier 3 - Скрытый копеечный чип STM32F407 (ПАРАДОКС КОПЕЕЧНОГО ЧИПА)
        stm32_t3 = Component(
            product_id=p1.id,
            parent_id=valve_t2.id,
            name="Микроконтроллер ARM Cortex-M4 STM32F407VGT6",
            article="STM32F407VGT6",
            tier=3,
            hs_code="8542319010",
            country_code="CH",
            manufacturer="STMicroelectronics (Швейцария/США)",
            unit_cost_rub=1850.0,
            quantity=4.0,
            criticality=1.0,
            country_risk=0.95,
            analog_availability=0.05,
            analog_status="NO_ANALOGS",
            cfi_score=calc_cfi(1.0, 0.95, 0.05), # 0.9025
            is_chokepoint=True,
            lead_time_days=180,
            notes="КРИТИЧЕСКИЙ УЗЕЛ! Чип за 1850 ₽. Без него гидроблок не работает, станок парализован. Поставляется по серому импорту.",
        )
        session.add(stm32_t3)

        # Tier 3 - Датчик давления
        danfoss_t3 = Component(
            product_id=p1.id,
            parent_id=valve_t2.id,
            name="Датчик давления MBS-3000 (0-400 bar)",
            article="MBS3000-060G",
            tier=3,
            hs_code="9026202000",
            country_code="DK",
            manufacturer="Danfoss A/S (Дания)",
            unit_cost_rub=42000.0,
            quantity=6.0,
            criticality=0.9,
            country_risk=0.90,
            analog_availability=0.70,
            analog_status="REQUIRES_REWORK",
            cfi_score=calc_cfi(0.9, 0.90, 0.70),
            is_chokepoint=False,
            lead_time_days=90,
        )
        session.add(danfoss_t3)

        # Tier 1 - Двигатель ЯМЗ-536
        eng_t1 = Component(
            product_id=p1.id,
            name="Дизельный двигатель ЯМЗ-536-Лесник (312 л.с.)",
            article="YMZ-536-L",
            tier=1,
            hs_code="8408209907",
            country_code="RU",
            manufacturer="ПАО «Автодизель»",
            unit_cost_rub=3800000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.0,
            analog_availability=0.95,
            analog_status="FULL_COMPATIBLE",
            cfi_score=0.0,
            is_chokepoint=False,
            lead_time_days=30,
        )
        session.add(eng_t1)
        await session.flush()

        # Tier 2 - Топливная рампа Common Rail
        cr_t2 = Component(
            product_id=p1.id,
            parent_id=eng_t1.id,
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
            analog_status="REQUIRES_REWORK",
            cfi_score=0.04,
            is_chokepoint=False,
            lead_time_days=45,
        )
        session.add(cr_t2)
        await session.flush()

        # Tier 3 - Скрытые форсунки Bosch
        bosch_t3 = Component(
            product_id=p1.id,
            parent_id=cr_t2.id,
            name="Электромагнитная форсунка высокого давления CRI2",
            article="0445120153",
            tier=3,
            hs_code="8409990009",
            country_code="DE",
            manufacturer="Robert Bosch GmbH (Германия)",
            unit_cost_rub=85000.0,
            quantity=6.0,
            criticality=1.0,
            country_risk=0.95,
            analog_availability=0.15,
            analog_status="NO_ANALOGS",
            cfi_score=calc_cfi(1.0, 0.95, 0.15),
            is_chokepoint=True,
            lead_time_days=120,
            notes="КРИТИЧЕСКИЙ УЗЕЛ! 14-й пакет санкций ЕС перекрыл прямые поставки. Зависимость двигателя.",
        )
        session.add(bosch_t3)

        # Tier 1 - Бортовой компьютер 'Кедр-М'
        comp_t1 = Component(
            product_id=p1.id,
            name="Бортовая система таксации и управления «Кедр-М»",
            article="KEDR-M-SYS",
            tier=1,
            hs_code="8471410000",
            country_code="RU",
            manufacturer="АО «Концерн НПО Аврора»",
            unit_cost_rub=1950000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.0,
            analog_availability=0.85,
            analog_status="FULL_COMPATIBLE",
            cfi_score=0.0,
            is_chokepoint=False,
            lead_time_days=30,
        )
        session.add(comp_t1)
        await session.flush()

        # Tier 2 - Плата энкодеров
        dsp_t2 = Component(
            product_id=p1.id,
            parent_id=comp_t1.id,
            name="Плата быстродействующего сбора данных с энкодеров",
            article="DSP-BOARD-V3",
            tier=2,
            hs_code="8473302008",
            country_code="RU",
            manufacturer="ООО «Северная Электроника»",
            unit_cost_rub=650000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.2,
            analog_availability=0.6,
            analog_status="REQUIRES_REWORK",
            cfi_score=0.08,
            is_chokepoint=False,
            lead_time_days=45,
        )
        session.add(dsp_t2)
        await session.flush()

        # Tier 3 - ПЛИС Xilinx (США)
        xilinx_t3 = Component(
            product_id=p1.id,
            parent_id=dsp_t2.id,
            name="ПЛИС FPGA Spartan-6 XC6SLX45-2CSG324I",
            article="XC6SLX45-2CSG324I",
            tier=3,
            hs_code="8542399010",
            country_code="US",
            manufacturer="AMD / Xilinx Inc. (США)",
            unit_cost_rub=4500.0,
            quantity=2.0,
            criticality=1.0,
            country_risk=1.0,
            analog_availability=0.0,
            analog_status="NO_ANALOGS",
            cfi_score=calc_cfi(1.0, 1.0, 0.0), # 1.0 (Максимальный стоп-фактор)
            is_chokepoint=True,
            lead_time_days=240,
            notes="АБСОЛЮТНЫЙ CHOKEPOINT (CFI = 1.0). Обрабатывает оптические датчики ствола. Запрет экспортного контроля США.",
        )
        session.add(xilinx_t3)

        # Отечественные аналоги для Харвестера
        analogs_p1 = [
            Analog(
                component_id=stm32_t3.id,
                name="32-разрядный отечественный микроконтроллер MIK32 «Амур»",
                manufacturer="АО «ПКК Микрон» (г. Зеленоград)",
                country_code="RU",
                unit_cost_rub=2400.0,
                redesign_cost_rub=450000.0,
                lead_time_days=30,
                compatibility_score=0.75,
                compatibility_status="REQUIRES_REWORK",
                description="Российский микроконтроллер на ядре RISC-V. Требует доработки разводки платы, но полностью исключает санкционные риски.",
            ),
            Analog(
                component_id=stm32_t3.id,
                name="Микроконтроллер К1921ВК01Т (ARM Cortex-M4F)",
                manufacturer="АО «НИИЭТ» (г. Воронеж)",
                country_code="RU",
                unit_cost_rub=3100.0,
                redesign_cost_rub=350000.0,
                lead_time_days=45,
                compatibility_score=0.85,
                compatibility_status="FULL_COMPATIBLE",
                description="Аппаратно совместимый отечественный чип с аппаратным ШИМ для гидроблоков.",
            ),
            Analog(
                component_id=bosch_t3.id,
                name="Форсунка электроуправляемая АЗПИ F-002",
                manufacturer="ООО «АЗПИ» (г. Барнаул)",
                country_code="RU",
                unit_cost_rub=62000.0,
                redesign_cost_rub=150000.0,
                lead_time_days=25,
                compatibility_score=0.90,
                compatibility_status="FULL_COMPATIBLE",
                description="Отечественная форсунка Common Rail, полностью сертифицирована для ЯМЗ-536.",
            ),
        ]
        session.add_all(analogs_p1)

        # =========================================================================
        # ПРОДУКТ 2: 5-осевой центр ЧПУ СТ-500 «Вектор» (СТРАТЕГИЧЕСКИЙ СТАНОК ОПК)
        # =========================================================================
        p2 = Product(
            name="5-осевой фрезерный обрабатывающий центр ЧПУ СТ-500 «Вектор»",
            article="CNC-5AX-500",
            category="Станкостроение и робототехника",
            target_industry="28.4 Высокоточное станкостроение",
            enterprise_name="АО «Станкомаш-Холдинг»",
            enterprise_inn="3702654120",
            enterprise_city="г. Иваново",
            total_cost_rub=68500000.0,
            is_strategic=True,
            strategic_priority="CRITICAL",
            strategic_notes="Критический производитель прецизионного станочного оборудования для двигателестроения, авиастроения и ОПК России.",
            description="5-координатный фрезерный центр для обработки лопаток турбин и титановых авиационных деталей. Де-юре 84 балла, де-факто уязвим по японским ШВП и немецким энкодерам.",
        )
        session.add(p2)
        await session.flush()

        # Tier 1 - Станина и портал
        frame_t1 = Component(
            product_id=p2.id,
            name="Чугунная монолитная станина и портал СТ-500",
            article="FRAME-ST500",
            tier=1,
            hs_code="8457109009",
            country_code="RU",
            manufacturer="АО «Станкомаш-Холдинг»",
            unit_cost_rub=24000000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.0,
            analog_availability=1.0,
            analog_status="FULL_COMPATIBLE",
            cfi_score=0.0,
            is_chokepoint=False,
            lead_time_days=30,
        )
        session.add(frame_t1)
        await session.flush()

        # Tier 1 - Шпиндельный узел
        spindle_t1 = Component(
            product_id=p2.id,
            name="Высокоскоростной мотор-шпиндель 24 000 об/мин",
            article="SPINDLE-24K",
            tier=1,
            hs_code="8466937000",
            country_code="RU",
            manufacturer="ООО «Прецизионная Механика»",
            unit_cost_rub=14500000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.0,
            analog_availability=0.9,
            analog_status="FULL_COMPATIBLE",
            cfi_score=0.0,
            is_chokepoint=False,
            lead_time_days=45,
        )
        session.add(spindle_t1)
        await session.flush()

        # Tier 2 - Сервопривод подач
        servo_t2 = Component(
            product_id=p2.id,
            parent_id=frame_t1.id,
            name="Прецизионная система линейных подач по 5 осям",
            article="DRIVE-5AX-SYS",
            tier=2,
            hs_code="8483402100",
            country_code="RU",
            manufacturer="ООО «Привод-Инжиниринг»",
            unit_cost_rub=8200000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.1,
            analog_availability=0.6,
            analog_status="REQUIRES_REWORK",
            cfi_score=0.04,
            is_chokepoint=False,
            lead_time_days=60,
        )
        session.add(servo_t2)
        await session.flush()

        # Tier 3 - Скрытый энкодер Heidenhain (Германия)
        encoder_t3 = Component(
            product_id=p2.id,
            parent_id=servo_t2.id,
            name="Оптическая линейка и круговой энкодер Heidenhain RCN-8380",
            article="RCN-8380-001",
            tier=3,
            hs_code="9031803400",
            country_code="DE",
            manufacturer="Dr. Johannes Heidenhain GmbH (Германия)",
            unit_cost_rub=380000.0,
            quantity=5.0,
            criticality=1.0,
            country_risk=0.95,
            analog_availability=0.10,
            analog_status="NO_ANALOGS",
            cfi_score=calc_cfi(1.0, 0.95, 0.10), # 0.855
            is_chokepoint=True,
            lead_time_days=150,
            notes="КРИТИЧЕСКИЙ УЗЕЛ! Без оптической точности 1 мкм станок теряет класс точности и не может обрабатывать лопатки турбин.",
        )
        session.add(encoder_t3)

        # Tier 3 - Скрытые японские ШВП THK
        thk_t3 = Component(
            product_id=p2.id,
            parent_id=servo_t2.id,
            name="Прецизионная шарико-винтовая пара THK C3 Ground Ball Screw",
            article="THK-BSR-4010",
            tier=3,
            hs_code="8483403000",
            country_code="JP",
            manufacturer="THK Co., Ltd. (Япония)",
            unit_cost_rub=195000.0,
            quantity=5.0,
            criticality=1.0,
            country_risk=0.95,
            analog_availability=0.20,
            analog_status="POORLY_COMPATIBLE",
            cfi_score=calc_cfi(1.0, 0.95, 0.20), # 0.76
            is_chokepoint=True,
            lead_time_days=180,
            notes="Япония заблокировала экспорт прецизионных направляющих класса C3 в РФ.",
        )
        session.add(thk_t3)

        # =========================================================================
        # ПРОДУКТ 3: Зерноуборочный комбайн TORUM 785 (РОСТСЕЛЬМАШ)
        # =========================================================================
        p3 = Product(
            name="Зерноуборочный роторный комбайн TORUM 785",
            article="TORUM-785-RU",
            category="Сельскохозяйственное машиностроение",
            target_industry="28.3 Сельскохозяйственное машиностроение",
            enterprise_name="ООО «КЗ Ростсельмаш»",
            enterprise_inn="6166001230",
            enterprise_city="г. Ростов-на-Дону",
            total_cost_rub=28500000.0,
            is_strategic=False,
            strategic_priority="NORMAL",
            strategic_notes="Крупнейший отечественный производитель уборочной сельхозтехники гражданского сектора.",
            description="Высокопроизводительный роторный комбайн для уборки зерновых на полях высокой урожайности.",
        )
        session.add(p3)
        await session.flush()

        harv_t1 = Component(
            product_id=p3.id,
            name="Роторное молотильно-сепарирующее устройство ARS",
            article="ARS-TORUM-01",
            tier=1,
            hs_code="8433510009",
            country_code="RU",
            manufacturer="ООО «КЗ Ростсельмаш»",
            unit_cost_rub=11200000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.0,
            analog_availability=1.0,
            analog_status="FULL_COMPATIBLE",
            cfi_score=0.0,
            is_chokepoint=False,
            lead_time_days=20,
        )
        session.add(harv_t1)

        hydro_t2 = Component(
            product_id=p3.id,
            parent_id=harv_t1.id,
            name="Гидростатическая трансмиссия ГСТ-112",
            article="GST-112-RSM",
            tier=2,
            hs_code="8481209009",
            country_code="BY",
            manufacturer="ОАО «Салео» (Республика Беларусь)",
            unit_cost_rub=2400000.0,
            quantity=1.0,
            criticality=1.0,
            country_risk=0.0,
            analog_availability=0.9,
            analog_status="FULL_COMPATIBLE",
            cfi_score=0.0,
            is_chokepoint=False,
            lead_time_days=30,
        )
        session.add(hydro_t2)
        await session.flush()

        can_t3 = Component(
            product_id=p3.id,
            parent_id=hydro_t2.id,
            name="Микросхема интерфейса CAN-шины TJA1051",
            article="TJA1051TK",
            tier=3,
            hs_code="8542319010",
            country_code="CH",
            manufacturer="NXP Semiconductors",
            unit_cost_rub=340.0,
            quantity=12.0,
            criticality=0.8,
            country_risk=0.95,
            analog_availability=0.50,
            analog_status="REQUIRES_REWORK",
            cfi_score=calc_cfi(0.8, 0.95, 0.50),
            is_chokepoint=False,
            lead_time_days=60,
        )
        session.add(can_t3)

        # 7. Официальные сертификаты
        cert1 = Certificate(
            product_id=p1.id,
            reg_number="RU-МПТ-719/2026-08412",
            status=ComplianceStatusEnum.COMPLIANT,
            pp719_points=78,
            ad_valorem_pct=88.5,
            defacto_localization_pct=41.2,
            vulnerability_gap_pct=47.3,
            certified_by="Минпромторг России • Департамент ДСПСДМ",
            qr_verification_url="https://gisp.gov.ru/pp719/cert/RU-MPT-719-2026-08412",
            digital_signature_hash=hashlib.sha256(b"MINPROMTORG_STAMP_RU_719_2026_LESTECHMASH").hexdigest(),
            expires_at=datetime.utcnow() + timedelta(days=365),
        )
        cert2 = Certificate(
            product_id=p2.id,
            reg_number="RU-МПТ-719/2026-09155",
            status=ComplianceStatusEnum.COMPLIANT,
            pp719_points=84,
            ad_valorem_pct=79.2,
            defacto_localization_pct=32.4,
            vulnerability_gap_pct=46.8,
            certified_by="Минпромторг России • Департамент станкостроения",
            qr_verification_url="https://gisp.gov.ru/pp719/cert/RU-MPT-719-2026-09155",
            digital_signature_hash=hashlib.sha256(b"MINPROMTORG_STAMP_RU_719_2026_STANKOMASH").hexdigest(),
            expires_at=datetime.utcnow() + timedelta(days=365),
        )
        session.add_all([cert1, cert2])

        # 8. Начальные записи в неизменяемый журнал аудита
        audit_p1 = AuditLog(
            event_type="SYSTEM_INITIAL_AUDIT",
            actor_id=1,
            actor_role=AuditActorTypeEnum.REGULATOR,
            resource_type="product",
            resource_id=p1.id,
            details={
                "action": "BOM_DECOMPOSITION_VERIFIED",
                "summary": "Выявлено 3 скрытых chokepoint-узла 3-го уровня (STM32, Bosch CRI, Xilinx Spartan-6)",
                "paper_loc": 88.5,
                "defacto_loc": 41.2,
                "vulnerability_gap": 47.3,
            },
            hash_sha256=hashlib.sha256(b"AUDIT_SEED_P1").hexdigest(),
        )
        session.add(audit_p1)

        await session.commit()
        print("✓ База данных MatryoshkaAudit успешно заполнена эталонными данными реальных предприятий!")


if __name__ == "__main__":
    asyncio.run(seed_database())
