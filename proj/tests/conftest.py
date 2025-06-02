from django.test import RequestFactory
from django.core.cache import cache
from products.models import Shop, Category, Product
import pytest
from django.contrib.auth import get_user_model
from cart.models import Order, OrderItem


@pytest.fixture
def user(db):
    """Создаёт тестового пользователя."""
    User = get_user_model()
    return User.objects.create_user(username='testuser', password='secret')


@pytest.fixture
def order_with_item(db, user, product_factory, category_tree):
    """
    Создаёт заказ с одним товаром и прикладывает сам товар
    к объекта order.product, чтобы тесты могли к нему обращаться.
    """
    # создаём товар
    prod = product_factory("OrderedProd", category=category_tree['root'])
    # создаём заказ (у вас требуется поле amount)
    order = Order.objects.create(
        user=user,
        status='new',
        amount=prod.price,  # обязательно для NOT NULL
    )
    # создаём позицию заказа
    OrderItem.objects.create(
        order=order,
        product=prod,
        quantity=1,
        price=prod.price
    )
    # прикладываем товар к заказу
    order.product = prod
    return order


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def shop(db):
    return Shop.objects.create(
        title="ShopTest",
        slug="shop-test",
        type="self-employed",
        address="Addr",
        INN="123456789012",
        payment_account="000111222",
        BIC="123456789",
    )


@pytest.fixture
def category_tree(db):
    # создаём простое дерево: root → child → grand
    root = Category.objects.create(title="Root", slug="root")
    child = Category.objects.create(title="Child", slug="child", parent=root)
    grand = Category.objects.create(title="Grand", slug="grand", parent=child)
    return {"root": root, "child": child, "grand": grand}


@pytest.fixture
def product_factory(db, shop):
    """
    Фабрика, принимающая:
      - name (str)
      - category (Category) или None
      - price (float)
      - items_left (int)
      - **extras для полей модели (length, weight, diameter и т.д.)
    """

    def make(name, category=None, price=10.0, items_left=5, **extras):
        obj = Product.objects.create(
            name=name,
            shop=shop,
            price=price,
            items_left=items_left,
            verified=True,  # <— добавляем
            warehouse_city="City",
            shipping_width=1.0, shipping_length=1.0,
            shipping_height=1.0, shipping_weight=0.5,
            **extras
        )
        if category is not None:
            obj.category.add(category)
        return obj

    return make
