# tests/users/test_users_views.py

import uuid
import pytest
from decimal import Decimal
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.core.paginator import Page

from products.models import Shop, Category, Product
from cart.models import Order, OrderItem, StoreSalesReport
from users.models import CustomUser as User


# -----------------------------
# Fixtures
# -----------------------------

@pytest.fixture
def user_factory(db):
    """Создаёт пользователя с паролем 'pw'."""

    def make(username="user", password="pw", **kwargs):
        u = User(username=username, email=kwargs.get("email", f"{username}@example.com"))
        u.set_password(password)
        for field in ("first_name", "last_name", "patronymic", "phone_number"):
            if field in kwargs:
                setattr(u, field, kwargs[field])
        u.save()
        if kwargs.get("shop"):
            u.shop = kwargs["shop"]
            u.save()
        return u

    return make


@pytest.fixture
def shop_factory(db):
    """Создаёт магазин с уникальным slug."""

    def make(**kwargs):
        defaults = {
            "title": "ShopTest",
            # делаем slug уникальным
            "slug": f"shop-{uuid.uuid4().hex[:8]}",
            "type": "ip",
            "address": "Addr",
            "INN": "111",
            "OGRNIP": "222",
            "OGRN": "",
            "payment_account": "acc",
            "BIC": "bic",
            "verified": True,
        }
        defaults.update(kwargs)
        return Shop.objects.create(**defaults)

    return make


@pytest.fixture
def category_tree(db):
    """Создаёт древо категорий: root → child → grand."""
    root = Category.objects.create(title="Root", slug="root")
    child = Category.objects.create(title="Child", slug="child", parent=root)
    grand = Category.objects.create(title="Grand", slug="grand", parent=child)
    return {"root": root, "child": child, "grand": grand}


@pytest.fixture
def product_factory(db, category_tree):
    """Создаёт товар, привязывает к leaf-категории и магазину."""

    def make(name, shop, category=None, price=10.0, items_left=5):
        p = Product.objects.create(
            name=name,
            shop=shop,
            price=Decimal(price),
            items_left=items_left,
            verified=True,
            warehouse_city="City",
            shipping_width=1,
            shipping_length=1,
            shipping_height=1,
            shipping_weight=1,
        )
        # по умолчанию leaf-категория 'grand'
        p.category.set([category or category_tree["grand"]])
        return p

    return make


@pytest.fixture
def order_factory(db, user_factory, shop_factory, product_factory):
    """Создаёт заказ и OrderItem'ы, устанавливает сумму."""

    def make(user=None, shop=None, items=None, **order_kwargs):
        user = user or user_factory()
        shop = shop or shop_factory()
        defaults = {
            "user": user,
            "shop": shop,
            "customer_last_name": "Ln",
            "customer_first_name": "Fn",
            "customer_email": "c@example.com",
            "customer_phone": "+70000000000",
            "delivery_method": "by_courier",
            "amount": Decimal("0.00"),
        }
        defaults.update(order_kwargs)
        order = Order.objects.create(**defaults)
        total = Decimal("0.00")
        items = items or [({}, 1)]
        for idx, (prod_kwargs, qty) in enumerate(items, start=1):
            prod = product_factory(f"prod{idx}", shop=shop, **prod_kwargs)
            OrderItem.objects.create(order=order, product=prod, price=prod.price, quantity=qty)
            total += prod.price * qty
        order.amount = total
        order.save()
        return order

    return make


@pytest.fixture
def store_sales_report_factory(db, shop_factory):
    """Создаёт StoreSalesReport для данного магазина."""

    def make(shop=None):
        shop = shop or shop_factory()
        today = timezone.now().date()
        report = StoreSalesReport.objects.create(
            shop=shop,
            start_date=today.replace(day=1),
            end_date=today,
            revenue=Decimal("0.00"),
            products_performance={},
            category_performance={},
        )
        return report

    return make


# -----------------------------
# Tests for users/views.py
# -----------------------------

class TestPersonalInformationEdit:
    def test_get_renders_form(self, client, user_factory):
        user = user_factory()
        client.login(username=user.username, password="pw")
        resp = client.get(reverse("users:personal_information"))
        assert resp.status_code == 200
        assert "form" in resp.context
        assert resp.context["form"].instance == user

    def test_post_updates_user(self, client, user_factory):
        user = user_factory(last_name="Old", first_name="Old", patronymic="Old")
        client.login(username=user.username, password="pw")
        data = {
            "username": user.username,
            "email": user.email,
            "last_name": "New",
            "first_name": "New",
            "patronymic": "New",
            "phone_number": user.phone_number or "",
        }
        resp = client.post(reverse("users:personal_information"), data)
        assert isinstance(resp, HttpResponseRedirect)
        user.refresh_from_db()
        assert user.last_name == "New"
        assert user.patronymic == "New"


class TestPersonalAccountOrders:
    def test_redirect_if_not_authenticated(self, client):
        resp = client.get(reverse("users:orders"))
        assert resp.status_code == 302

    def test_orders_list_paginated(self, client, user_factory, order_factory):
        user = user_factory()
        # 30 заказов для одного пользователя
        for _ in range(24):
            order_factory(user=user)
        client.login(username=user.username, password="pw")
        resp = client.get(reverse("users:orders"))
        assert resp.status_code == 200
        orders = resp.context["orders"]
        assert isinstance(orders, Page)
        assert orders.paginator.count == 24


class TestPersonalAccountOrderDetail:
    def test_view_own_order(self, client, user_factory, order_factory):
        user = user_factory()
        order = order_factory(user=user)
        client.login(username=user.username, password="pw")
        resp = client.get(reverse("users:order_detail", args=[order.pk]))
        assert resp.status_code == 200
        assert resp.context["order"] == order

    def test_not_owner_redirects(self, client, user_factory, order_factory):
        u1 = user_factory(username="u1")
        u2 = user_factory(username="u2")
        order = order_factory(user=u1)
        client.login(username=u2.username, password="pw")
        resp = client.get(reverse("users:order_detail", args=[order.pk]))
        assert isinstance(resp, HttpResponseRedirect)
        assert reverse("users:orders") in resp.url


@pytest.mark.django_db
class TestShopDocsView:

    def test_get_renders(self, client, user_factory):
        user = user_factory()
        client.login(username=user.username, password="pw")
        resp = client.get(reverse("users:shop_docs"))
        assert resp.status_code == 200
        assert "form" in resp.context
        assert resp.context["shop"] is None

    def test_post_creates_shop(self, client, user_factory):
        # Пользователь без магазина
        user = user_factory(shop=None)
        client.login(username=user.username, password="pw")

        data = {
            "title": "NewShop",
            "slug": "new-shop",
            "type": "individual_entrepreneur",
            "address": "Address",
            "INN": "123456789",
            "OGRNIP": "123456789",
            "OGRN": "",
            "payment_account": "123456789",
            "BIC": "123456789",
        }
        resp = client.post(reverse("users:shop_docs"), data)

        # Ожидаем редирект на тот же URL
        assert resp.status_code == 302
        assert isinstance(resp, HttpResponseRedirect)
        assert resp.url == reverse("users:shop_docs")

        # Магазин создался в базе
        assert Shop.objects.filter(slug="new-shop").exists()

        # Пользователь привязан к новому магазину
        user.refresh_from_db()
        assert user.shop is not None
        assert user.shop.slug == "new-shop"

        # Теперь по GET на тот же URL вернётся форма с instance=новый shop
        get_resp = client.get(reverse("users:shop_docs"))
        assert get_resp.status_code == 200
        assert get_resp.context["shop"].slug == "new-shop"
        form = get_resp.context["form"]
        assert form.instance == user.shop


class TestShopOrdersView:
    def test_redirect_if_no_shop(self, client, user_factory):
        user = user_factory()
        client.login(username=user.username, password="pw")
        resp = client.get(reverse("users:shop_orders"))
        assert isinstance(resp, HttpResponseRedirect)
        assert reverse("users:shop_docs") in resp.url

    def test_lists_paid_orders(self, client, user_factory, shop_factory, order_factory):
        shop = shop_factory()
        user = user_factory(shop=shop)
        paid_order = order_factory(user=user, shop=shop)
        paid_order.paid = True
        paid_order.save()
        unpaid_order = order_factory(user=user, shop=shop)
        unpaid_order.paid = False
        unpaid_order.save()

        client.login(username=user.username, password="pw")
        resp = client.get(reverse("users:shop_orders"))
        orders = resp.context["orders"]
        assert all(o.paid for o in orders)


class TestUpdateOrderStatusView:
    def test_post_updates_status(self, client, user_factory, shop_factory, order_factory):
        shop = shop_factory()
        user = user_factory(shop=shop)
        order = order_factory(user=user, shop=shop)
        client.login(username=user.username, password="pw")
        data = {"status": "in_assembly", "page": "2", "q": "x"}
        resp = client.post(reverse("users:update_order_status", args=[order.pk]), data)
        assert isinstance(resp, HttpResponseRedirect)
        order.refresh_from_db()
        assert order.status == "in_assembly"
        assert f"#order-{order.pk}" in resp.url


class TestShopProductsView:
    def test_redirect_if_unverified(self, client, user_factory, shop_factory):
        shop = shop_factory(verified=False)
        user = user_factory(shop=shop)
        client.login(username=user.username, password="pw")
        resp = client.get(reverse("users:shop_products"))
        assert isinstance(resp, HttpResponseRedirect)
        assert reverse("users:shop_docs") in resp.url

    def test_add_product(self, client, user_factory, shop_factory, category_tree):
        shop = shop_factory(verified=True)
        user = user_factory(shop=shop)
        client.login(username=user.username, password="pw")
        cat = category_tree["grand"]  # leaf-категория
        data = {
            "add_product": "",
            "name": "Prod",
            "description": "D",
            "price": "10",
            "items_left": "1",
            "warehouse_city": "C",
            "shipping_width": "1",
            "shipping_length": "1",
            "shipping_height": "1",
            "shipping_weight": "1",
            "category": [cat.pk],
        }
        resp = client.post(reverse("users:shop_products"), data)
        assert isinstance(resp, HttpResponseRedirect)
        assert Product.objects.filter(shop=shop, name="Prod").exists()


class TestUpdateProductStockView:
    def test_post_updates_stock(self, client, user_factory, shop_factory, product_factory):
        shop = shop_factory()
        user = user_factory(shop=shop)
        prod = product_factory("X", shop=shop)
        client.login(username=user.username, password="pw")
        data = {"items_left": "5", "show": "on", "page": "1", "q": ""}
        resp = client.post(reverse("users:update_product_stock", args=[prod.pk]), data)
        assert isinstance(resp, HttpResponseRedirect)
        prod.refresh_from_db()
        assert prod.show is True


class TestEditProductView:
    def test_get_renders(self, client, user_factory, shop_factory, product_factory, category_tree):
        shop = shop_factory()
        user = user_factory(shop=shop)
        cat = category_tree["child"]
        prod = product_factory("E", shop=shop, category=cat)
        client.login(username=user.username, password="pw")
        resp = client.get(reverse("users:edit_product", args=[prod.pk]))
        assert resp.status_code == 200
        assert resp.context["product"] == prod


class TestShopStatisticsView:
    def test_redirect_if_no_shop(self, client, user_factory):
        user = user_factory()
        client.login(username=user.username, password="pw")
        resp = client.get(reverse("users:shop_statistics"))
        assert isinstance(resp, HttpResponseRedirect)
        assert reverse("users:shop_docs") in resp.url

    def test_lists_reports(self, client, user_factory, shop_factory, store_sales_report_factory):
        shop = shop_factory()
        user = user_factory(shop=shop)
        for _ in range(5):
            store_sales_report_factory(shop=shop)
        client.login(username=user.username, password="pw")
        resp = client.get(reverse("users:shop_statistics"))
        reports = resp.context["reports"]
        assert isinstance(reports, Page)
        assert reports.paginator.count == 5
