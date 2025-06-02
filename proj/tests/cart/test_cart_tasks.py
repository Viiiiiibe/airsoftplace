# tests/cart/test_cart_tasks.py
import pytest
from decimal import Decimal
from datetime import date
import calendar
from django.utils import timezone
from django.core import mail

from cart.tasks import (
    update_order_status,
    decrease_product_quantity,
    update_store_sales_report,
    send_email_to_owner,
    send_email_to_customer,
    create_monthly_reports,
    delete_order_with_canceled_payment,
)
from cart.models import Order, OrderItem, StoreSalesReport, ShippingAddress
from products.models import Shop


@pytest.fixture
def order_factory(db, user, shop, product_factory):
    """
    Factory to create an Order with arbitrary OrderItems.
    Usage:
        order = order_factory(
            order_kwargs={'customer_email': 'foo@bar.com'},
            items_info=[({'price': Decimal('5.00'), 'items_left': 10}, 2), …]
        )
    """
    def make(order_kwargs=None, items_info=None):
        order_kwargs = order_kwargs or {}
        # базовые поля заказа
        defaults = {
            'user': user,
            'shop': shop,
            'customer_last_name': 'Ln',
            'customer_first_name': 'Fn',
            'customer_email': 'c@example.com',
            'customer_phone': '+70000000000',
            'delivery_method': 'by_courier',
            'amount': Decimal('0.00'),
        }
        defaults.update(order_kwargs)
        order = Order.objects.create(**defaults)

        total = Decimal('0.00')
        items_info = items_info or [({}, 1)]
        # дефолтная категория из product_factory, если не передана
        default_cat = getattr(product_factory, '__defaults__', [None])[0]

        for idx, (prod_kwargs, qty) in enumerate(items_info, start=1):
            name = prod_kwargs.pop('name', f"prod_{order.pk}_{idx}")
            cat = prod_kwargs.pop('category', default_cat)
            prod = product_factory(name, cat, **prod_kwargs)
            OrderItem.objects.create(
                order=order,
                product=prod,
                price=prod.price,
                quantity=qty
            )
            # приводим цену к Decimal на всякий случай
            total += Decimal(prod.price) * qty

        order.amount = total
        order.save(update_fields=['amount'])
        return order

    return make


@pytest.mark.django_db
def test_update_order_status(order_factory):
    order = order_factory(items_info=[({'price': Decimal('9.00'), 'items_left': 5}, 1)])
    assert not order.paid and order.status != 'in_assembly'

    update_order_status(order.id)
    order.refresh_from_db()
    assert order.paid is True
    assert order.status == 'in_assembly'


@pytest.mark.django_db
def test_decrease_product_quantity(order_factory):
    # items_left=5, qty=2 → станет 3
    order = order_factory(items_info=[({'price': Decimal('3.00'), 'items_left': 5}, 2)])
    item = order.items.first()
    before = item.product.items_left

    decrease_product_quantity(order.id)
    item.product.refresh_from_db()
    assert item.product.items_left == before - item.quantity


@pytest.fixture
def order_for_report(order_factory):
    # один товар по цене 7, qty=3 → amount=21
    return order_factory(items_info=[({'price': Decimal('7.00'), 'items_left': 10}, 3)])


@pytest.mark.django_db
def test_update_store_sales_report(order_for_report):
    order = order_for_report
    # вызываем таску
    update_store_sales_report(order.id)

    today = timezone.now().date()
    # после фикса в коде tasks.py (update_fields=['revenue','updated']), отчет должен быть создан
    report = StoreSalesReport.objects.get(
        shop=order.shop,
        start_date__lte=today,
        end_date__gte=today
    )
    # revenue == сумма заказа
    assert report.revenue == order.amount

    # performance по товару
    pid = str(order.items.first().product.pk)
    assert report.products_performance.get(pid) == order.items.first().quantity

    # performance по категории (хотя бы для одной категории)
    for cat in order.items.first().product.category.all():
        assert report.category_performance.get(cat.slug) == order.items.first().quantity


@pytest.fixture
def order_with_owner_and_address(order_factory, user, shop):
    # делаем пользователя владельцем магазина, задаём email
    user.email = "owner@example.com"
    try:
        setattr(user, 'shop', shop)
        user.save()
    except Exception:
        pass

    # создаём адрес доставки
    ShippingAddress.objects.create(user=user, country="RU", region="Rg", city="Ct")

    return order_factory(
        order_kwargs={'customer_email': 'customer@ex.com'},
        items_info=[({'price': Decimal('5.00'), 'items_left': 2}, 1)]
    )


@pytest.mark.django_db
def test_send_email_to_owner(order_with_owner_and_address):
    mail.outbox = []
    send_email_to_owner(order_with_owner_and_address.id)
    # если у shop.owner есть email, то придёт хотя бы одно письмо
    assert any("Новый заказ" in m.subject for m in mail.outbox)


@pytest.mark.django_db
def test_send_email_to_customer(order_with_owner_and_address):
    mail.outbox = []
    send_email_to_customer(order_with_owner_and_address.id)
    # первым письмом будет письмо клиенту
    assert mail.outbox
    assert "Ваш заказ" in mail.outbox[0].subject
    assert order_with_owner_and_address.customer_email in mail.outbox[0].to


@pytest.mark.django_db
def test_delete_order_with_canceled_payment(order_factory):
    order = order_factory()
    assert Order.objects.filter(pk=order.id).exists()

    delete_order_with_canceled_payment(order.id)
    assert not Order.objects.filter(pk=order.id).exists()


@pytest.fixture
def shops_pair(shop):
    # создаём ещё один магазин
    other = Shop.objects.create(
        title="OtherShop", slug="other", address="Addr",
        INN="222", payment_account="333", BIC="444"
    )
    return shop, other


@pytest.mark.django_db
def test_create_monthly_reports(shops_pair):
    now = timezone.now().date()
    # вычисляем следующий месяц
    if now.month == 12:
        yr, mo = now.year + 1, 1
    else:
        yr, mo = now.year, now.month + 1
    first = date(yr, mo, 1)
    last = date(yr, mo, calendar.monthrange(yr, mo)[1])

    # для первого магазина отчёт уже есть
    StoreSalesReport.objects.create(
        shop=shops_pair[0],
        start_date=first,
        end_date=last,
        revenue=Decimal('0.00'),
        products_performance={},
        category_performance={}
    )
    # запускаем таску
    create_monthly_reports()

    # после неё отчёты должны быть на оба магазина
    reports = StoreSalesReport.objects.filter(start_date=first, end_date=last)
    shop_ids = {r.shop_id for r in reports}
    assert shop_ids == {shops_pair[0].pk, shops_pair[1].pk}
