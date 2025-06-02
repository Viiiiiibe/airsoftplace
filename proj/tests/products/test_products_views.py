import pytest
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth import get_user_model

from products.models import Review

pytestmark = pytest.mark.django_db


def test_index_context(client, category_tree, product_factory):
    root = category_tree['root']
    p1 = product_factory("Good", category=root)
    p2 = product_factory("Bad", category=root)
    user = get_user_model().objects.create_user("u2", "u2@example.com", "pw")
    Review.objects.create(product=p1, user=user, rating=5)
    Review.objects.create(product=p2, user=user, rating=2)

    resp = client.get(reverse('index'))
    assert resp.status_code == 200
    products = resp.context['products']
    assert list(products) == [p1]


def test_all_products_context(client, category_tree, product_factory):
    root = category_tree['root']
    product_factory("X1", category=root, price=10)
    product_factory("X2", category=root, price=20)

    url = reverse('all_products') + '?q=X&prod_count=1&sort_by=price'
    resp = client.get(url)
    assert resp.status_code == 200

    ctx = resp.context
    assert ctx['keyword'] == 'X'
    assert ctx['sort_parameter'] == 'price'
    assert len(ctx['page_obj'].object_list) == 1
    assert 'price_data_for_filters' in ctx
    assert 'length_data_for_filters' in ctx


def test_categories_and_subcategories_context(client, category_tree):
    root = category_tree['root']
    child = category_tree['child']

    resp1 = client.get(reverse('categories'))
    assert resp1.status_code == 200
    assert list(resp1.context['categories']) == [root]

    resp2 = client.get(reverse('subcategories', args=[root.slug]))
    assert resp2.status_code == 200
    assert resp2.context['category'] == root
    assert list(resp2.context['subcategories']) == [child]


def test_category_products_context(client, category_tree, product_factory):
    child = category_tree['child']
    p_direct = product_factory("D", category=child)
    _ = product_factory("N", category=category_tree['grand'])

    url = reverse('category_products', args=[child.slug]) + '?prod_count=10'
    resp = client.get(url)
    assert resp.status_code == 200

    ctx = resp.context
    assert ctx['category'] == child
    assert list(ctx['page_obj'].object_list) == [p_direct]
    assert ctx['sort_parameter'] == '-pub_date'
    assert 'price_data_for_filters' in ctx


def test_shops_and_shop_categories_context(client, shop, category_tree, product_factory):
    product_factory("X", category=category_tree['grand'])
    cache.set(f"shop_{shop.slug}_info_cache", {'foo': 1})

    resp1 = client.get(reverse('shops'))
    assert resp1.status_code == 200
    assert 'shops' in resp1.context

    resp2 = client.get(reverse('shop_categories', args=[shop.slug]))
    assert resp2.status_code == 200
    ctx2 = resp2.context
    assert ctx2['shop'] == shop
    assert isinstance(ctx2['categories'], list)
    assert ctx2['shop_info'] == {'foo': 1}


def test_shop_subcategories_and_products_context(client, shop, category_tree, product_factory):
    product_factory("P1", category=category_tree['grand'])
    cache.set(f"shop_{shop.slug}_info_cache", {'bar': 2})

    url_sub = reverse('shop_subcategories', args=[shop.slug, category_tree['root'].slug])
    resp_sub = client.get(url_sub)
    assert resp_sub.status_code == 200
    ctx_sub = resp_sub.context
    assert ctx_sub['shop'] == shop
    assert ctx_sub['category'] == category_tree['root']
    assert isinstance(ctx_sub['subcategories'], list)
    assert ctx_sub['shop_info'] == {'bar': 2}

    url_prod = (
            reverse('shop_category_products', args=[shop.slug, category_tree['child'].slug])
            + '?prod_count=5'
    )
    resp_prod = client.get(url_prod)
    assert resp_prod.status_code == 200
    ctx_prod = resp_prod.context
    assert ctx_prod['shop'] == shop
    assert ctx_prod['category'] == category_tree['child']
    assert 'page_obj' in ctx_prod
    assert ctx_prod['shop_info'] == {'bar': 2}
    assert 'price_data_for_filters' in ctx_prod


def test_product_detail_and_reviews_context(client, user, order_with_item):
    # используем товар из фикстуры
    p = order_with_item.product

    # до логина
    resp = client.get(reverse('product_detail', args=[p.id]))
    assert resp.status_code == 200
    ctx = resp.context
    assert ctx['product'] == p
    assert ctx['can_review'] is False

    # после логина — can_review=True
    client.login(username='testuser', password='secret')
    resp2 = client.get(reverse('product_detail', args=[p.id]))
    assert resp2.context['can_review'] is True


def test_product_reviews_context(client, user, order_with_item):
    p = order_with_item.product
    # создаём пару отзывов
    Review.objects.create(product=p, user=user, rating=4)
    Review.objects.create(product=p, user=user, rating=5)

    resp = client.get(reverse('product_reviews', args=[p.id]))
    assert resp.status_code == 200
    assert resp.context['product'] == p
    assert len(resp.context['page_obj'].object_list) == 2


def test_add_and_edit_review_views(client, user, order_with_item):
    p = order_with_item.product
    url_add = reverse('add_review', args=[p.id])

    # без логина → редирект
    resp0 = client.get(url_add)
    assert resp0.status_code == 302

    # с логином → форма
    client.login(username='testuser', password='secret')
    resp1 = client.get(url_add)
    assert resp1.status_code == 200

    # POST создания
    resp2 = client.post(url_add, {'rating': 4, 'text': 'Ok'}, follow=True)
    assert resp2.status_code == 200
    assert Review.objects.filter(product=p, user=user).exists()

    # редактирование
    rev = Review.objects.get(product=p, user=user)
    url_edit = reverse('edit_review', args=[rev.id])
    resp3 = client.get(url_edit)
    assert resp3.status_code == 200
    resp4 = client.post(url_edit, {'rating': 5, 'text': 'New'})
    assert resp4.status_code == 302
    rev.refresh_from_db()
    assert rev.rating == 5
    assert rev.text == 'New'
