import json
import pytest
from decimal import Decimal
from django.test import RequestFactory
from django.http import HttpResponse
from cart.webhooks import yookassa_webhook
from cart.models import Order
from cart.tasks import (
    update_order_status,
    decrease_product_quantity,
    update_store_sales_report,
    send_email_to_owner,
    send_email_to_customer,
    delete_order_with_canceled_payment
)
from yookassa.domain.common import SecurityHelper
from yookassa.domain.notification import (
    WebhookNotificationEventType,
    WebhookNotificationFactory
)


@pytest.fixture(autouse=True)
def rf():
    return RequestFactory()


@pytest.fixture
def order(db, user, shop):
    """Создаем тестовый заказ с payment_id и суммой 123.45"""
    o = Order.objects.create(
        user=user,
        shop=shop,
        customer_last_name="LN",
        customer_first_name="FN",
        customer_email="c@example.com",
        customer_phone="+70000000000",
        delivery_method="by_courier",
        amount=Decimal("123.45"),
    )
    o.payment_id = "pay_1"
    o.save(update_fields=["payment_id"])
    return o


class DummyNotification:
    def __init__(self, event, obj):
        self.event = event
        self.object = obj


class DummyResponseObject:
    def __init__(self, id, amount_value):
        self.id = id

        # структура: response_object.amount.value
        class Amt:
            def __init__(self, v):
                self.value = v

        self.amount = Amt(amount_value)


@pytest.mark.django_db
def test_untrusted_ip(rf, monkeypatch):
    """Если IP не доверен — сразу 400"""
    req = rf.post("/webhook/", data=b"{}", content_type="application/json")
    req.META["REMOTE_ADDR"] = "1.2.3.4"
    monkeypatch.setattr(SecurityHelper, "is_ip_trusted", lambda self, ip: False)
    resp = yookassa_webhook(req)
    assert isinstance(resp, HttpResponse) and resp.status_code == 400


@pytest.mark.django_db
def test_payment_succeeded_amount_match_triggers_tasks(rf, monkeypatch, order):
    """PAYMENT_SUCCEEDED + корректная сумма → 200 и вызов .delay всех задач кроме delete"""
    payload = {"event": WebhookNotificationEventType.PAYMENT_SUCCEEDED}
    dummy_resp = DummyResponseObject(order.payment_id, str(order.amount))
    # Monkeypatch фабрику уведомлений
    monkeypatch.setattr(SecurityHelper, "is_ip_trusted", lambda self, ip: True)
    monkeypatch.setattr(WebhookNotificationFactory, "create",
                        lambda self, j: DummyNotification(WebhookNotificationEventType.PAYMENT_SUCCEEDED, dummy_resp)
                        )

    # Пусть все .delay запишем вызовы
    called = []
    for task in (
            update_order_status,
            decrease_product_quantity,
            update_store_sales_report,
            send_email_to_owner,
            send_email_to_customer,
            delete_order_with_canceled_payment
    ):
        monkeypatch.setattr(task, "delay", lambda order_id, t=task: called.append(t.__name__))

    req = rf.post("/webhook/",
                  data=json.dumps(payload).encode(),
                  content_type="application/json")
    req.META["REMOTE_ADDR"] = "127.0.0.1"
    resp = yookassa_webhook(req)
    assert resp.status_code == 200
    # delete_order_with_canceled_payment не должен вызываться
    assert set(called) == {
        "update_order_status",
        "decrease_product_quantity",
        "update_store_sales_report",
        "send_email_to_owner",
        "send_email_to_customer",
    }


@pytest.mark.django_db
def test_payment_succeeded_amount_mismatch_logs_400(rf, monkeypatch, order):
    """PAYMENT_SUCCEEDED + mismatch суммы → 400 и нет вызова задач"""
    payload = {"event": WebhookNotificationEventType.PAYMENT_SUCCEEDED}
    dummy_resp = DummyResponseObject(order.payment_id, "999.99")
    monkeypatch.setattr(SecurityHelper, "is_ip_trusted", lambda self, ip: True)
    monkeypatch.setattr(WebhookNotificationFactory, "create",
                        lambda self, j: DummyNotification(WebhookNotificationEventType.PAYMENT_SUCCEEDED, dummy_resp)
                        )

    called = []
    for task in (
            update_order_status,
            decrease_product_quantity,
            update_store_sales_report,
            send_email_to_owner,
            send_email_to_customer,
            delete_order_with_canceled_payment
    ):
        monkeypatch.setattr(task, "delay", lambda order_id, t=task: called.append(t.__name__))

    req = rf.post("/webhook/",
                  data=json.dumps(payload).encode(),
                  content_type="application/json")
    req.META["REMOTE_ADDR"] = "127.0.0.1"
    resp = yookassa_webhook(req)
    assert resp.status_code == 400
    assert called == []


@pytest.mark.django_db
def test_payment_succeeded_order_not_found(rf, monkeypatch):
    """PAYMENT_SUCCEEDED + несуществующий payment_id → 400"""
    payload = {"event": WebhookNotificationEventType.PAYMENT_SUCCEEDED}
    dummy_resp = DummyResponseObject("unknown", "1.23")
    monkeypatch.setattr(SecurityHelper, "is_ip_trusted", lambda self, ip: True)
    monkeypatch.setattr(WebhookNotificationFactory, "create",
                        lambda self, j: DummyNotification(WebhookNotificationEventType.PAYMENT_SUCCEEDED, dummy_resp)
                        )
    req = rf.post("/webhook/",
                  data=json.dumps(payload).encode(),
                  content_type="application/json")
    req.META["REMOTE_ADDR"] = "127.0.0.1"
    resp = yookassa_webhook(req)
    assert resp.status_code == 400


@pytest.mark.django_db
def test_payment_canceled_triggers_delete(rf, monkeypatch, order):
    """PAYMENT_CANCELED → 200 и вызов только delete_order_with_canceled_payment"""
    payload = {"event": WebhookNotificationEventType.PAYMENT_CANCELED}
    dummy_resp = DummyResponseObject(order.payment_id, str(order.amount))
    monkeypatch.setattr(SecurityHelper, "is_ip_trusted", lambda self, ip: True)
    monkeypatch.setattr(WebhookNotificationFactory, "create",
                        lambda self, j: DummyNotification(WebhookNotificationEventType.PAYMENT_CANCELED, dummy_resp)
                        )
    called = []
    monkeypatch.setattr(delete_order_with_canceled_payment, "delay",
                        lambda order_id: called.append("delete_order_with_canceled_payment"))
    req = rf.post("/webhook/",
                  data=json.dumps(payload).encode(),
                  content_type="application/json")
    req.META["REMOTE_ADDR"] = "127.0.0.1"
    resp = yookassa_webhook(req)
    assert resp.status_code == 200
    assert called == ["delete_order_with_canceled_payment"]


@pytest.mark.django_db
def test_unknown_event_returns_400(rf, monkeypatch):
    """Любое другое событие → 400"""
    payload = {"event": "SOME_OTHER"}
    monkeypatch.setattr(SecurityHelper, "is_ip_trusted", lambda self, ip: True)
    monkeypatch.setattr(WebhookNotificationFactory, "create",
                        lambda self, j: DummyNotification("SOME_OTHER", DummyResponseObject("", "")))
    req = rf.post("/webhook/",
                  data=json.dumps(payload).encode(),
                  content_type="application/json")
    req.META["REMOTE_ADDR"] = "127.0.0.1"
    resp = yookassa_webhook(req)
    assert resp.status_code == 400
