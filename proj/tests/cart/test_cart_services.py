import pytest
from decimal import Decimal

from cart.services import (
    get_city_zone,
    determine_tariff_zone,
    calculate_shipping_cost,
    get_cdek_shipping_cost,
    SPECIAL_CITIES_ZONE4,
    SPECIAL_CITIES_ZONE5,
    SPECIAL_CITIES_ZONE6,
    TARIFF_MATRIX,
    TARIFF_TABLE,
)


@pytest.mark.parametrize("city,expected_zone", [
    ("Москва", 1),
    ("санкт-петербург", 1),
    ("  Балашиха  ", 2),
    ("Неизвестный город", None),
])
def test_get_city_zone(city, expected_zone):
    assert get_city_zone(city) == expected_zone


@pytest.mark.parametrize("from_zone,to_zone,from_city,to_city,expected", [
    # non-tuple entry
    (1, 3, "москва", "казань", TARIFF_MATRIX[1][3]),
    # tuple entry, from_zone=4,to_zone=4, city in SPECIAL_CITIES_ZONE4
    (4, 4, next(iter(SPECIAL_CITIES_ZONE4)), "каменск-шахтинский", TARIFF_MATRIX[4][4][0]),
    # tuple entry, from_zone=4,to_zone=4, city not in SPECIAL_CITIES_ZONE4
    (4, 4, "московский", "каменск-шахтинский", TARIFF_MATRIX[4][4][1]),
    # from 5 to 6, city in SPECIAL_CITIES_ZONE5
    (5, 6, next(iter(SPECIAL_CITIES_ZONE5)), "омск", TARIFF_MATRIX[5][6][0]),
    # from 6 to 6, city in SPECIAL_CITIES_ZONE6
    (6, 6, next(iter(SPECIAL_CITIES_ZONE6)), "сургут", TARIFF_MATRIX[6][6][0]),
])
def test_determine_tariff_zone_variants(from_zone, to_zone, from_city, to_city, expected):
    result = determine_tariff_zone(from_zone, to_zone, from_city, to_city)
    assert result == expected


@pytest.mark.parametrize("tariff_zone,method,weight,expected", [
    # weight <= 1 → base only
    (1, "Курьером", 0.5, Decimal(TARIFF_TABLE[1]["courier"][0])),
    (2, "Пункт выдачи", 1, Decimal(TARIFF_TABLE[2]["pickup"][0])),
    # weight > 1 → base + (weight-1)*per_kg
    (3, "Курьером", 3, Decimal(TARIFF_TABLE[3]["courier"][0]) + (Decimal(2) * Decimal(TARIFF_TABLE[3]["courier"][1]))),
    (
            0, "Пункт выдачи", 5,
            Decimal(TARIFF_TABLE[0]["pickup"][0]) + (Decimal(4) * Decimal(TARIFF_TABLE[0]["pickup"][1]))),
])
def test_calculate_shipping_cost(tariff_zone, method, weight, expected):
    got = calculate_shipping_cost(tariff_zone, method, Decimal(weight))
    assert got == expected.quantize(Decimal("1.00"))


@pytest.fixture(autouse=True)
def clear_cache(monkeypatch):
    # ensure no external cache interference
    from django.core.cache import cache
    cache.clear()


def test_get_cdek_shipping_cost_same_city(monkeypatch):
    # if warehouse_city == delivery_city → zone 0
    cost = get_cdek_shipping_cost("москва", "москва", Decimal("2.5"), "Курьером")
    # tariff_zone=0 → courier prices
    base, per_kg = TARIFF_TABLE[0]["courier"]
    expected = Decimal(base) + (Decimal("1.5") * Decimal(per_kg))
    assert cost == expected.quantize(Decimal("1.00"))


def test_get_cdek_shipping_cost_invalid_city():
    # unknown city names → returns None
    assert get_cdek_shipping_cost("xxx", "yyy", Decimal("1.0"), "Курьером") is None


def test_get_cdek_shipping_cost_various(monkeypatch):
    # choose two known cities in different zones, e.g. москва (1) → казань (3)
    cost = get_cdek_shipping_cost("москва", "казань", Decimal("1.0"), "Пункт выдачи")
    # tariff_zone = TARIFF_MATRIX[1][3] == 3 → pickup prices for zone 3
    base, _ = TARIFF_TABLE[3]["pickup"]
    assert cost == Decimal(base).quantize(Decimal("1.00"))

    # test that exceptions inside get_cdek_shipping_cost return None
    # monkeypatch determine_tariff_zone to throw
    monkeypatch.setattr("cart.services.determine_tariff_zone",
                        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError()))
    assert get_cdek_shipping_cost("москва", "казань", Decimal("1.0"), "Курьером") is None
