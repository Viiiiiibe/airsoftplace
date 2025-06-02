import pytest
from django.urls import reverse
from django.test import Client, RequestFactory
from decimal import Decimal
from django.core.cache import cache
from django.contrib.sessions.backends.db import SessionStore
from cart.models import Order, OrderItem
from products.models import Category, Product
from products.utils import set_shop_info_cache
from products.tasks import find_recommended_products_for_user
from core.context_processors.recommendations_data import recommendations_data
import json


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def rf():
    return RequestFactory()


# --- Cart integration tests ---

def test_cart_add_and_view(client, product_factory):
    prod = product_factory("ProdCart", category=None)
    # Add to cart
    resp_add = client.post(reverse('cart:add-to-cart'), {'action': 'post', 'product_id': prod.id, 'product_qty': 1})
    assert resp_add.status_code == 200
    data = resp_add.json()
    assert data['qty'] == 1 and data['product'] == prod.name
    # View cart
    resp_view = client.get(reverse('cart:cart-view'))
    assert resp_view.status_code == 200
    grouped = list(resp_view.context['grouped_items'])
    assert len(grouped) == 1
    items = grouped[0]['items']
    assert items[0]['product'].pk == prod.pk and items[0]['qty'] == 1


def test_cart_update_and_view(client, product_factory):
    prod = product_factory("ProdUpd", category=None)
    client.post(reverse('cart:add-to-cart'), {'action': 'post', 'product_id': prod.id, 'product_qty': 1})
    resp_upd = client.post(reverse('cart:update-to-cart'), {'action': 'post', 'product_id': prod.id, 'product_qty': 3})
    assert resp_upd.status_code == 200 and resp_upd.json()['qty'] == 3
    resp_view = client.get(reverse('cart:cart-view'))
    items = list(resp_view.context['grouped_items'])[0]['items']
    assert items[0]['qty'] == 3


def test_cart_delete_and_view(client, product_factory):
    prod = product_factory("ProdDel", category=None)
    client.post(reverse('cart:add-to-cart'), {'action': 'post', 'product_id': prod.id, 'product_qty': 2})
    resp_del = client.post(reverse('cart:delete-to-cart'), {'action': 'post', 'product_id': prod.id})
    assert resp_del.status_code == 200 and resp_del.json()['qty'] == 0
    resp_view = client.get(reverse('cart:cart-view'))
    assert not list(resp_view.context['grouped_items'])


# --- Shipping cost integration ---

def test_order_view_shipping_cost(client, product_factory, shop):
    prod = Product.objects.create(
        name='Ship', shop=shop, price=50.0, items_left=10,
        verified=True, warehouse_city='волгоград', shipping_width=10,
        shipping_length=10, shipping_height=10, shipping_weight=1
    )
    prod.category.add(Category.objects.create(title='C', slug='c'))
    client.post(reverse('cart:add-to-cart'), {'action': 'post', 'product_id': prod.id, 'product_qty': 2})
    resp = client.post(reverse('cart:order-view', args=[shop.slug]),
                       {'find_shipping_cost_to_city': 'волгоград', 'find_shipping_cost_with_method': 'Пункт выдачи'})
    assert resp.status_code == 200
    assert resp.json()['shipping_cost'] == '165.00'


# --- Products & views integration ---

def test_all_products_and_filters(client, product_factory):
    p1 = product_factory('X1', category=None, price=10)
    product_factory('X2', category=None, price=20)
    resp = client.get(reverse('all_products'), {'q': 'X', 'prod_count': 1, 'sort_by': 'price'})
    assert resp.status_code == 200
    ctx = resp.context
    assert list(ctx['page_obj'])[0].pk == p1.pk
    assert 'price_data_for_filters' in ctx and 'length_data_for_filters' in ctx


def test_category_products_and_filters(client, product_factory, category_tree):
    child = category_tree['child']
    product_factory('D', category=child, price=10)
    z = product_factory('Z', category=child, price=100)
    product_factory('N', category=category_tree['root'], price=50)
    resp = client.get(reverse('category_products', args=[child.slug]),
                      {'prod_count': 10, 'sort_by': 'price', 'min_price': 90})
    assert resp.status_code == 200
    ctx = resp.context
    assert list(ctx['page_obj']) == [z]
    assert ctx['category'] == child and 'price_data_for_filters' in ctx


def test_shop_categories_and_cache(client, user, shop, category_tree, product_factory):
    grand = category_tree['grand']
    p = product_factory('X', category=grand)
    p.shop = shop
    p.save()
    user.email = 'owner@test.com'
    user.save()
    set_shop_info_cache(shop.slug)
    resp = client.get(reverse('shop_categories', args=[shop.slug]))
    assert resp.status_code == 200
    ctx = resp.context
    assert ctx['shop'] == shop and ctx['categories']
    assert ctx['shop_info'] == cache.get(f'shop_{shop.slug}_info_cache')


def test_shop_subcategories_and_cache(client, shop, category_tree, product_factory):
    child = category_tree['child']
    p = product_factory('Y', category=child)
    p.shop = shop
    p.save()
    set_shop_info_cache(shop.slug)
    resp = client.get(reverse('shop_subcategories', args=[shop.slug, category_tree['root'].slug]))
    assert resp.status_code == 200
    ctx = resp.context
    assert ctx['shop'] == shop and ctx['category'] == category_tree['root']
    assert list(ctx['subcategories'])
    assert 'shop_info' in ctx


def test_shop_products_and_filters(client, shop, category_tree, product_factory):
    grand = category_tree['grand']
    p1 = product_factory('P1', category=grand, price=15)
    p1.shop = shop
    p1.save()
    p2 = product_factory('P2', category=grand, price=20)
    p2.shop = shop
    p2.save()
    resp = client.get(reverse('shop_category_products', args=[shop.slug, grand.slug]), {'max_price': 16})
    assert resp.status_code == 200
    ctx = resp.context
    assert list(ctx['page_obj']) == [p1]
    assert ctx['shop'] == shop and ctx['category'] == grand and 'price_data_for_filters' in ctx


# --- Recommendations integration ---

def test_recommendations_data_and_task(monkeypatch, rf, user, product_factory, category_tree):
    p1 = product_factory('p1', category=category_tree['root'], price=10)
    p2 = product_factory('p2', category=category_tree['root'], price=20)
    order = Order.objects.create(user=user, amount=Decimal('10.00'))
    OrderItem.objects.create(order=order, product=p1, quantity=1, price=p1.price)
    request = rf.get('/')
    request.user = user
    request.session = SessionStore()
    request.session['recently_viewed'] = [p2.id]
    # trigger task
    calls = {}
    monkeypatch.setattr(find_recommended_products_for_user, 'delay', lambda u, v: calls.setdefault('args', (u, v)))
    result1 = recommendations_data(request)
    assert calls['args'] == (user.pk, [p2.id]) and 'recommended_products' in result1
    # second call uses cache
    result2 = recommendations_data(request)
    assert list(result2['recommended_products']) == list(result1['recommended_products'])


# --- YooKassa Webhook integration tests ---

# Helper to build payload
def make_payment_notification(order, success=True):
    event = 'payment.succeeded' if success else 'payment.canceled'
    return json.dumps({
        'event': event,
        'object': {
            'id': order.payment_id,
            'amount': {'value': str(order.amount), 'currency': 'RUB'}
        }
    })


@pytest.mark.django_db
def test_yookassa_webhook_success(monkeypatch, client, product_factory, shop, user):
    prod = product_factory('WP', category=None)
    order = Order.objects.create(user=user, shop=shop, amount=Decimal('5.00'), payment_id='pay123')
    OrderItem.objects.create(order=order, product=prod, quantity=2, price=Decimal('2.50'))
    # Mock trusted IP and factory
    from yookassa.domain.common import SecurityHelper
    from yookassa.domain.notification import WebhookNotificationFactory, WebhookNotificationEventType
    dummy_obj = type('O', (), {'id': order.payment_id, 'amount': type('A', (), {'value': str(order.amount)})()})

    class DummyNotification:
        event = WebhookNotificationEventType.PAYMENT_SUCCEEDED
        object = dummy_obj

    monkeypatch.setattr(SecurityHelper, 'is_ip_trusted', lambda self, ip: True)
    monkeypatch.setattr(WebhookNotificationFactory, 'create', lambda self, j: DummyNotification())
    # Patch tasks
    from cart.tasks import update_order_status, decrease_product_quantity, update_store_sales_report, \
        send_email_to_owner, send_email_to_customer
    called = []
    for task_name, task in [
        ('update_order_status', update_order_status),
        ('decrease_product_quantity', decrease_product_quantity),
        ('update_store_sales_report', update_store_sales_report),
        ('send_email_to_owner', send_email_to_owner),
        ('send_email_to_customer', send_email_to_customer),
    ]:
        monkeypatch.setattr(task, 'delay', lambda oid, name=task_name: called.append(name))
    # Send webhook
    resp = client.post(reverse('cart:webhook-yookassa'), data=make_payment_notification(order),
                       content_type='application/json', REMOTE_ADDR='127.0.0.1')
    assert resp.status_code == 200
    # Ensure all tasks triggered
    assert set(called) == {'update_order_status', 'decrease_product_quantity', 'update_store_sales_report',
                           'send_email_to_owner', 'send_email_to_customer'}


@pytest.mark.django_db
def test_yookassa_webhook_canceled(monkeypatch, client, product_factory, shop, user):
    prod = product_factory('WP', category=None)
    order = Order.objects.create(user=user, shop=shop, amount=Decimal('5.00'), payment_id='pay321')
    OrderItem.objects.create(order=order, product=prod, quantity=1, price=Decimal('5.00'))
    from yookassa.domain.common import SecurityHelper
    from yookassa.domain.notification import WebhookNotificationFactory, WebhookNotificationEventType
    dummy_obj = type('O', (), {'id': order.payment_id, 'amount': type('A', (), {'value': str(order.amount)})()})

    class DummyNotification:
        event = WebhookNotificationEventType.PAYMENT_CANCELED
        object = dummy_obj

    monkeypatch.setattr(SecurityHelper, 'is_ip_trusted', lambda self, ip: True)
    monkeypatch.setattr(WebhookNotificationFactory, 'create', lambda self, j: DummyNotification())
    from cart.tasks import delete_order_with_canceled_payment
    deleted = []
    monkeypatch.setattr(delete_order_with_canceled_payment, 'delay', lambda oid: deleted.append(oid))
    resp = client.post(reverse('cart:webhook-yookassa'), data=make_payment_notification(order, False),
                       content_type='application/json', REMOTE_ADDR='127.0.0.1')
    assert resp.status_code == 200
    # Verify delete task
    assert deleted == [order.id]


# --- User views & support/task integration tests ---
@pytest.mark.django_db
def test_personal_account_order_detail_sends_to_support(monkeypatch, rf, client, user, shop, product_factory,
                                                        category_tree):
    # Prepare order owned by user
    prod = product_factory('SP', category=None)
    order = Order.objects.create(user=user, shop=shop, amount=Decimal('10.00'))
    OrderItem.objects.create(order=order, product=prod, quantity=1, price=prod.price)
    # Login as user
    client.force_login(user)
    # Patch support email task
    from users.tasks import send_mail_to_support_task
    sent = []
    monkeypatch.setattr(send_mail_to_support_task, 'delay',
                        lambda oid, shop_title, u_pk, msg: sent.append((oid, shop_title, u_pk, msg)))
    # POST with message
    url = reverse('users:order_detail', args=[order.pk])
    resp = client.post(url, {'message': 'HELP'})
    assert resp.status_code == 200
    # Task should be queued
    assert sent == [(order.pk, order.shop.title, user.pk, 'HELP')]


@pytest.mark.django_db
def test_update_order_status_and_send_email(monkeypatch, client, user, shop, order_with_item):
    # Make user a shop owner
    shop_owner = user
    shop_owner.shop = shop
    shop_owner.save()
    # Prepare order in shop
    order = order_with_item
    order.shop = shop
    order.save(update_fields=['shop'])
    client.force_login(shop_owner)
    # Patch status email task
    from users.tasks import send_order_status_email
    sent = []
    monkeypatch.setattr(send_order_status_email, 'delay', lambda oid: sent.append(oid))
    # POST status update
    url = reverse('users:update_order_status', args=[order.pk])
    resp = client.post(url, {'status': 'in_assembly', 'page': '2', 'q': 'test'})
    # Should redirect with anchor
    assert resp.status_code == 302
    assert f'#order-{order.pk}' in resp.url
    # Order status updated
    order.refresh_from_db()
    assert order.status == 'in_assembly'
    # Task queued
    assert sent == [order.pk]
