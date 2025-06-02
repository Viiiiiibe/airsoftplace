import pytest
from django.urls import reverse

import uuid
from cart.models import ShippingAddress
from yookassa import Payment

from django.test import RequestFactory
from django.core.cache import cache
from decimal import Decimal

from products.models import Shop, Category, Product
from cart.models import Order, OrderItem

pytestmark = pytest.mark.django_db


@pytest.fixture
def shop(db):
    """
    Единый магазин для большинства тестов.
    slug генерируется уникальным, чтобы не было конфликтов.
    """
    return Shop.objects.create(
        title="ShopTest",
        slug=f"shop-{uuid.uuid4().hex[:8]}",
        type="self-employed",
        address="Россия, Москва, ул. Тест, 1",
        INN="123456789012",
        payment_account="000111222",
        BIC="123456789",
        verified=True
    )


@pytest.fixture
def shop_factory(db):
    """
    Фабрика для создания произвольных магазинов (используется в тесте перенаправления).
    """

    def make(title, slug, verified=True):
        return Shop.objects.create(
            title=title,
            slug=slug,
            type="self-employed",
            address="Россия, Москва, ул. Тест, 1",
            INN="123456789012",
            payment_account="000111222",
            BIC="123456789",
            verified=verified
        )

    return make


@pytest.fixture
def category_factory(db):
    """Простая фабрика для категорий."""

    def make(title="TestCat", slug="testcat"):
        return Category.objects.create(title=title, slug=slug)

    return make


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def product_factory(db, shop, category_factory):
    """
    Фабрика продуктов.
    Параметры:
      - name (str)
      - price (float)
      - items_left (int)
      - shop (Shop)  optional — если не передан, используется фикстурный shop
      - category (Category) optional — если не передан, создаётся через category_factory()
    """
    default_shop = shop

    def make(name,
             price=10.0,
             items_left=5,
             shop=None,
             category=None):
        used_shop = shop or default_shop
        used_cat = category or category_factory()
        p = Product.objects.create(
            name=name,
            price=price,
            items_left=items_left,
            warehouse_city='moscow',
            shipping_width=1,
            shipping_length=1,
            shipping_height=1,
            shipping_weight=0.5,
            shop=used_shop,
            verified=True,
            show=True
        )
        p.category.set([used_cat])
        return p

    return make


@pytest.fixture
def user(db):
    """Простая фикстура пользователя."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(username='testuser', password='secret')


@pytest.fixture
def order_with_item(db, user, product_factory, category_factory):
    """
    Заказ с одним товаром, чтобы тесты могли обращаться к order_with_item.product
    """
    prod = product_factory("OrderedProd", category=category_factory())
    order = Order.objects.create(
        user=user,
        status='new',
        amount=prod.price,
    )
    OrderItem.objects.create(
        order=order,
        product=prod,
        quantity=1,
        price=prod.price
    )
    order.product = prod
    return order


def test_cart_view_empty(client):
    """Пустая корзина показывает пустой grouped_items."""
    resp = client.get(reverse('cart:cart-view'))
    assert resp.status_code == 200
    assert 'grouped_items' in resp.context
    assert list(resp.context['grouped_items']) == []


def test_cart_add_update_delete(client, product_factory):
    prod = product_factory("P1", price=Decimal('10.00'), items_left=5)

    # ADD
    resp_add = client.post(reverse('cart:add-to-cart'), {
        'action': 'post',
        'product_id': prod.id,
        'product_qty': 2
    })
    assert resp_add.status_code == 200
    data = resp_add.json()
    assert data['qty'] == 2
    assert data['product'] == prod.name

    # UPDATE → 3 шт.
    resp_upd = client.post(reverse('cart:update-to-cart'), {
        'action': 'post',
        'product_id': prod.id,
        'product_qty': 3
    })
    assert resp_upd.status_code == 200
    upd = resp_upd.json()
    assert upd['qty'] == 3
    assert Decimal(upd['total']) == Decimal('30.00')

    # DELETE
    resp_del = client.post(reverse('cart:delete-to-cart'), {
        'action': 'post',
        'product_id': prod.id
    })
    assert resp_del.status_code == 200
    d = resp_del.json()
    assert d['qty'] == 0
    assert Decimal(d['total']) == Decimal('0.00')


def test_order_view_redirects(client, shop_factory):
    # несуществующий магазин → редирект в корзину
    resp1 = client.get(reverse('cart:order-view', args=['no-shop']))
    assert resp1.status_code == 302
    assert resp1.url.endswith(reverse('cart:cart-view'))

    # существующий, но корзина пуста → редирект
    shop = shop_factory('S', 's-slug')
    resp2 = client.get(reverse('cart:order-view', args=[shop.slug]))
    assert resp2.status_code == 302
    assert resp2.url.endswith(reverse('cart:cart-view'))


def test_order_view_get(client, product_factory):
    prod = product_factory("P2")
    shop = prod.shop

    # заполняем сессию напрямую
    session = client.session
    session['session_key'] = {
        str(prod.id): {'qty': 1, 'price': str(prod.price), 'shop_slug': shop.slug}
    }
    session.save()

    resp = client.get(reverse('cart:order-view', args=[shop.slug]))
    assert resp.status_code == 200
    ctx = resp.context
    assert 'items' in ctx and len(ctx['items']) == 1
    assert ctx['total_price'] == prod.price
    assert ctx['shop'] == shop
    assert 'form' in ctx


def test_order_view_calculate_shipping(monkeypatch, client, product_factory):
    prod = product_factory("P3")
    shop = prod.shop

    session = client.session
    session['session_key'] = {
        str(prod.id): {'qty': 1, 'price': str(prod.price), 'shop_slug': shop.slug}
    }
    session.save()

    url = reverse('cart:order-view', args=[shop.slug])

    # некорректный POST
    resp_bad = client.post(url, {'find_shipping_cost_to_city': ''})
    assert resp_bad.status_code == 400

    # правильный POST, мокируем стоимость
    monkeypatch.setattr('cart.views.get_cdek_shipping_cost', lambda w, c, g, m: Decimal('5.00'))
    resp = client.post(url, {
        'find_shipping_cost_to_city': 'anycity',
        'find_shipping_cost_with_method': 'courier'
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data['shipping_cost'] == '5.00'


def test_payment_pages(client):
    resp1 = client.get(reverse('cart:payment-success'))
    assert resp1.status_code == 200
    resp2 = client.get(reverse('cart:payment-error'))
    assert resp2.status_code == 200


@pytest.mark.django_db
def test_order_creation_and_payment_redirect(monkeypatch, client, user, shop, product_factory):
    """
    При POST без find_shipping_cost_to_city должно:
    1) через add-to-cart добавить товар в корзину
    2) создать ShippingAddress, Order и OrderItem
    3) вызвать Payment.create и сохранить payment_id
    4) очистить корзину
    5) сделать редирект на confirmation_url
    """
    # 1) подготовка пользователя и корзины
    user.shop = shop
    user.save()
    client.login(username=user.username, password='secret')

    prod = product_factory("Prod1", shop=shop)
    # кладём товар в корзину через API
    resp_add = client.post(reverse('cart:add-to-cart'), {
        'action': 'post',
        'product_id': prod.id,
        'product_qty': 2
    })
    assert resp_add.status_code == 200, "Не удалось добавить товар в корзину"

    # 2) подменяем Payment.create
    class DummyConfirmation:
        def __init__(self, url):
            self.confirmation_url = url

    class DummyPayment:
        def __init__(self, pid, url):
            self.id = pid
            self.confirmation = DummyConfirmation(url)

    dummy = DummyPayment('pay_123', 'https://confirm.test/123')
    monkeypatch.setattr(Payment, 'create', lambda params, key: dummy)

    # 3) данные POST для оформления
    data = {
        # поля формы MakingAnOrderForm
        'customer_last_name': 'LN',
        'customer_first_name': 'FN',
        'customer_patronymic': '',
        'customer_email': 'test@example.com',
        'customer_phone': '+79123456789',
        # поля доставки
        'shipping': 'Курьером',
        'courier-delivery-region': 'Регион',
        'courier-delivery-city': 'Город',
        'courier-delivery-street': 'Улица',
        'courier-delivery-house': '1',
        'courier-delivery-flat': '2',
        'courier-delivery-entrance': '3',
        'courier-delivery-floor': '4',
        'courier-delivery-intercom': '56',
    }

    # 4) POST на оформление заказа
    resp = client.post(reverse('cart:order-view', args=[shop.slug]), data)

    # 5) после успешного create → редирект (302) на confirmation_url
    assert resp.status_code == 302
    assert resp.url == dummy.confirmation.confirmation_url

    # проверяем создание заказа
    order = Order.objects.get(payment_id=dummy.id)
    assert order.user == user
    assert order.shop == shop
    assert order.amount == prod.price * 2

    # проверяем адрес доставки (достаём по user и игнорируем регистр)
    addr = ShippingAddress.objects.get(user=user)
    assert addr.city.lower() == 'город'
    assert addr.house == '1'

    # проверяем позицию заказа
    items = OrderItem.objects.filter(order=order)
    assert items.count() == 1
    assert items.first().product == prod
    assert items.first().quantity == 2

    # корзина должна быть очищена
    assert client.session.get('session_key', {}) == {}


@pytest.mark.django_db
def test_order_creation_payment_error_redirect(monkeypatch, client, user, shop, product_factory):
    """
    Если Payment.create бросает исключение, заказ удаляется
    и происходит редирект на страницу ошибки оплаты
    """
    # подготовка
    user.shop = shop
    user.save()
    client.login(username=user.username, password='secret')

    prod = product_factory("ErrProd", shop=shop)
    client.post(reverse('cart:add-to-cart'), {
        'action': 'post',
        'product_id': prod.id,
        'product_qty': 1
    })

    # 1) заставляем Payment.create падать
    monkeypatch.setattr(Payment, 'create', lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError()))

    # 2) данные POST с полями формы и доставкой
    data = {
        'customer_last_name': 'LN',
        'customer_first_name': 'FN',
        'customer_patronymic': '',
        'customer_email': 'test@example.com',
        'customer_phone': '+79123456789',
        'shipping': 'Пункт выдачи',
        'pickup-point-region': 'Rgn',
        'pickup-point-city': 'City',
        'pickup-point-street': 'Str',
        'pickup-point-house': '10',
    }

    # 3) POST на оформление заказа
    resp = client.post(reverse('cart:order-view', args=[shop.slug]), data)

    # 4) должно быть перенаправление на страницу ошибки оплаты
    assert resp.status_code == 302
    assert resp.url.endswith(reverse('cart:payment-error'))

    # 5) заказа в базе быть не должно
    assert not Order.objects.filter(shop=shop, user=user).exists()
