import pytest
from django.core.cache import cache
from products.services import (
    find_shop_categories,
    get_filtered_products_from_all,
    get_all_products_filters,
    get_category_filtered_products,
    get_category_filters,
    get_shop_filtered_products,
    get_shop_category_filters,
)

pytestmark = pytest.mark.django_db


def test_find_shop_categories_root(shop, category_tree, product_factory):
    # подвяжем товар к deepest (grand)
    product_factory("P1", category_tree["grand"])
    result = find_shop_categories(shop, None, cache_key="root_test")
    # единственный корень — Root
    assert result == [category_tree["root"]]

    # проверяем чтение из кэша
    fake = [category_tree["child"]]
    cache.set("root_test", fake, timeout=60)
    assert find_shop_categories(shop, None, cache_key="root_test") == fake


def test_find_shop_categories_subcategories(shop, category_tree, product_factory):
    product_factory("P2", category_tree["grand"])
    subs = find_shop_categories(shop, category_tree["root"], cache_key="sub_test")
    # только Child, т.к. товар лежит в его поддереве
    assert subs == [category_tree["child"]]


def test_get_filtered_products_from_all(request_factory, category_tree, product_factory):
    # создаём товары
    product_factory("FooBar", category_tree["root"], price=5.0, items_left=1)
    product_factory("Other", category_tree["root"], price=15.0, items_left=0)
    p3 = product_factory("FooBaz", category_tree["root"], price=25.0, items_left=10)

    req = request_factory.get("/", {"q": "Foo", "min_price": "10", "available": "1"})
    qs = get_filtered_products_from_all(req, keyword="Foo")
    ids = {p.id for p in qs}
    # должен пройти только p3 (название содержит Foo и price>=10 и items_left>0)
    assert ids == {p3.id}


def test_get_all_products_filters(category_tree, product_factory):
    # товары с разными price, length, diameter
    product_factory("A", category_tree["root"], price=1.2, length=10, diameter=0.5)
    product_factory("B", category_tree["root"], price=3.4, length=20, diameter=1.5)

    data = get_all_products_filters(keyword=None)
    # Проверяем агрегаты
    pr = data["price_data_for_filters"]
    assert pr["price__min"] == 1.2
    assert pr["price__max"] == 3.4

    ln = data["length_data_for_filters"]
    assert ln["length__min"] == 10
    assert ln["length__max"] == 20

    diams = {d["diameter"] for d in data["diameter_data_for_filters"]}
    assert diams == {0.5, 1.5}


def test_get_category_filtered_products(request_factory, category_tree, product_factory):
    """
    Проверяем, что фильтрация по категории учитывает только прямые связи,
    а не подкатегории.
    """
    a = product_factory("X", category_tree["child"], price=100)
    product_factory("Y", category_tree["grand"], price=200)

    # фильтрация по price>=150 возвращает пустой список (нет прямых продуктов)
    req = request_factory.get("/", {"min_price": "150"})
    qs = get_category_filtered_products(category_tree["child"], req)
    assert list(qs) == []

    # без фильтрации вернёт только a
    req2 = request_factory.get("/", {})
    qs2 = get_category_filtered_products(category_tree["child"], req2)
    assert list(qs2) == [a]


def test_get_category_filters(category_tree, product_factory):
    product_factory("M1", category_tree["child"], weight=10, principle_of_operation="op1")
    product_factory("M2", category_tree["child"], weight=20, principle_of_operation="op2")

    data = get_category_filters(category_tree["child"])
    weights = {w["weight"] for w in data["weight_data_for_filters"]}
    assert weights == {10, 20}

    pr = data["price_data_for_filters"]
    assert pr["price__min"] <= pr["price__max"]


def test_get_shop_filtered_and_category_filters(
        shop, category_tree, request_factory, product_factory
):
    pA = product_factory("A", category_tree["child"], price=50)
    product_factory("B", category_tree["grand"], price=150)

    # фильтрация по price>=100 возвращает пустой список (нет прямых продуктов)
    req = request_factory.get("/", {"min_price": "100"})
    qs_shop = get_shop_filtered_products(category_tree["child"], shop, req)
    assert list(qs_shop) == []

    # без фильтрации вернёт только pA
    req2 = request_factory.get("/", {})
    qs_shop2 = get_shop_filtered_products(category_tree["child"], shop, req2)
    assert list(qs_shop2) == [pA]

    filt_data = get_shop_category_filters(category_tree["child"], shop)
    pr = filt_data["price_data_for_filters"]
    assert pr["price__min"] <= pr["price__max"]
