# tests/users/test_tasks.py
import pytest
from django.core import mail
from proj.settings import EMAIL_HOST_USER, MANAGER_EMAIL
from django.contrib.auth import get_user_model

from cart.models import Order
from users.tasks import send_mail_to_support_task, send_order_status_email

User = get_user_model()


@pytest.mark.django_db
def test_send_mail_to_support_task():

    # Создаём тестового пользователя
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="password",
        first_name="First",
        last_name="Last",
        patronymic="Patron"
    )

    # Очистим почтовый ящик
    mail.outbox = []

    # Вызов задачи
    send_mail_to_support_task.delay(  # .delay() только имитируется, т к мы вызываем напрямую
        order_id=42,
        ordr_shop="ShopTitle",
        user_pk=user.pk,
        message="Help me!"
    )

    # Проверяем, что письмо отправлено именно одно
    assert len(mail.outbox) == 1
    m = mail.outbox[0]

    # Заголовки
    assert "Обращение покупателя по заказу 42" in m.subject
    assert m.from_email == EMAIL_HOST_USER
    assert m.to == [MANAGER_EMAIL]

    # Тело письма содержит данные пользователя и сообщение
    assert "testuser - test@example.com" in m.body
    assert "Last First Patron" in m.body  # порядок фамилия, имя, отчество
    assert "Заказ: 42 из ShopTitle" in m.body
    assert "Help me!" in m.body


@pytest.mark.django_db
def test_send_order_status_email():

    # Создаём тестовый заказ
    order = Order.objects.create(
        user=None,
        shop=None,
        customer_last_name="LN",
        customer_first_name="FN",
        customer_email="cust@example.com",
        customer_phone="+70000000000",
        delivery_method="by_courier",
        amount=0
    )

    # По умолчанию status = 'awaiting_payment'
    # Очищаем почтовый ящик
    mail.outbox = []

    # Вызов задачи
    send_order_status_email.delay(order.id)

    # Должно прийти одно письмо
    assert len(mail.outbox) == 1
    m = mail.outbox[0]

    # Проверяем заголовок и адреса
    assert m.subject == f"Обновление статуса заказа {order.id}"
    assert m.from_email == EMAIL_HOST_USER
    assert m.to == [order.customer_email]

    # В теле письма упоминается отображаемый статус заказа
    status_display = order.get_status_display()
    assert status_display in m.body
