import pytest
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from core.context_processors.recently_viewed import recently_viewed
from core.context_processors.recommendations_data import recommendations_data
from products.tasks import find_recommended_products_for_user
from cart.models import Order, OrderItem
from django.contrib.auth import get_user_model
from products.models import Product, Review

pytestmark = pytest.mark.django_db


def _get_request_with_session(user=None):
    """
    Возвращает RequestFactory‑запрос с инициализированной сессией и указанным user.
    """
    rf = RequestFactory()
    req = rf.get('/')
    # SessionMiddleware требует get_response
    middleware = SessionMiddleware(get_response=lambda r: None)
    middleware.process_request(req)
    req.session.save()
    req.user = user or AnonymousUser()
    return req


def test_recently_viewed_empty():
    req = _get_request_with_session()
    out = recently_viewed(req)
    assert out == {}


def test_recently_viewed_ordering(product_factory):
    # создаём три продукта
    p1 = product_factory("A", None)
    p2 = product_factory("B", None)
    p3 = product_factory("C", None)

    req = _get_request_with_session()
    req.session['recently_viewed'] = [p2.id, p3.id, p1.id]
    req.session.save()

    out = recently_viewed(req)
    recs = out['recently_viewed_products']
    assert [p.id for p in recs] == [p2.id, p3.id, p1.id]


def test_recommendations_data_anonymous_and_cache(monkeypatch):
    cache.clear()
    # создаём пару продуктов
    a = Product.objects.create(
        name="A", price=1.0, items_left=1,
        warehouse_city="X", shipping_width=1, shipping_length=1,
        shipping_height=1, shipping_weight=0.1,
        verified=True, show=True
    )
    b = Product.objects.create(
        name="B", price=2.0, items_left=1,
        warehouse_city="X", shipping_width=1, shipping_length=1,
        shipping_height=1, shipping_weight=0.1,
        verified=True, show=True
    )
    # даём обоим продуктам высокие оценки, чтобы avg_rating >= 4
    user = get_user_model().objects.create_user("temp", "temp@e", "pw")
    Review.objects.create(product=a, user=user, rating=5)
    Review.objects.create(product=b, user=user, rating=4)

    req = _get_request_with_session()
    # первое обращение — строит и кеширует популярное
    data1 = recommendations_data(req)
    recs1 = data1['recommended_products']
    # оба должны попасть в результаты
    assert set(p.id for p in recs1) == {a.id, b.id}
    assert cache.get("recommended_products_cache") is not None

    # второй вызов — читаем из кеша, delay не должен вызываться
    monkeypatch.setattr(find_recommended_products_for_user, 'delay',
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("delay shouldn't be called")))
    data2 = recommendations_data(req)
    recs2 = data2['recommended_products']
    assert set(p.id for p in recs2) == {a.id, b.id}


def test_recommendations_data_authenticated_triggers_task(monkeypatch):
    cache.clear()
    req = _get_request_with_session(user=get_user_model().objects.create_user("u", "u@e", "p"))
    req.session['recently_viewed'] = [1, 2, 3]
    req.session.save()

    called = {}

    def fake_delay(pk, viewed_ids):
        called['args'] = (pk, viewed_ids)

    monkeypatch.setattr(find_recommended_products_for_user, 'delay', fake_delay)

    data = recommendations_data(req)
    # проверяем, что задача запущена именно с нашими аргументами
    assert called['args'] == (req.user.pk, [1, 2, 3])
    # и при этом возвращается общий кешенный список
    assert 'recommended_products' in data


def test_find_recommended_products_for_user_caches_only_candidates(product_factory, user):
    cache.clear()
    # три продукта
    p1 = product_factory("P1", None, price=1.0, items_left=1)
    p2 = product_factory("P2", None, price=2.0, items_left=1)
    p3 = product_factory("P3", None, price=3.0, items_left=1)

    # заказ на p1
    order = Order.objects.create(user=user, status='new', amount=p1.price)
    OrderItem.objects.create(order=order, product=p1, quantity=1, price=p1.price)

    # просмотр p2
    viewed = [p2.id]

    # запускаем задачу
    find_recommended_products_for_user(user.pk, viewed)

    key = f"recommended_products_cache_user_{user.pk}"
    cached = cache.get(key)
    # единственным кандидатом остаётся p3
    assert isinstance(cached, list)
    assert len(cached) == 1
    assert cached[0].id == p3.id
