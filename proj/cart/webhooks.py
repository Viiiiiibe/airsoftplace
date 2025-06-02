import json
import logging
from decimal import Decimal
from django.http import HttpResponse
from yookassa.domain.common import SecurityHelper
from yookassa.domain.notification import (WebhookNotificationEventType,
                                          WebhookNotificationFactory)
from .models import Order
from .tasks import update_order_status, decrease_product_quantity, update_store_sales_report, send_email_to_owner, \
    send_email_to_customer, delete_order_with_canceled_payment

logger = logging.getLogger('django')


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def yookassa_webhook(request):
    ip = get_client_ip(request)  # Получите IP запроса
    if not SecurityHelper().is_ip_trusted(ip):
        return HttpResponse(status=400)

    # Извлечение JSON объекта из тела запроса
    event_json = json.loads(request.body)
    try:
        # Создание объекта класса уведомлений в зависимости от события
        notification_object = WebhookNotificationFactory().create(event_json)
        response_object = notification_object.object
        if notification_object.event == WebhookNotificationEventType.PAYMENT_SUCCEEDED:
            payment_id = response_object.id

            try:
                # Ищем заказ по payment_id
                order = Order.objects.get(payment_id=payment_id)

                # Проверяем совпадение суммы
                if Decimal(response_object.amount.value) != order.amount:
                    logger.error(
                        f"Amount mismatch for order {order.id}. Payment: {response_object.amount.value}, "
                        f"Order: {order.amount}")
                    return HttpResponse(status=400)

                # Обновляем статус заказа асинхронно
                update_order_status.delay(order.id)
                # Уменьшаем количество товаров асинхронно
                decrease_product_quantity.delay(order.id)
                # Обновляем отчет о продажах магазина асинхронно
                update_store_sales_report.delay(order.id)
                # Отправляем письмо владельцу магазина асинхронно
                send_email_to_owner.delay(order.id)
                # Отправляем письмо клиенту асинхронно
                send_email_to_customer.delay(order.id)

            except Order.DoesNotExist:
                logger.error(f"Order not found for payment ID: {payment_id}")
                return HttpResponse(status=400)

            except Exception as e:
                logger.error(f"Error updating order: {str(e)}")
                return HttpResponse(status=400)
        # Платеж отклонен
        elif notification_object.event == WebhookNotificationEventType.PAYMENT_CANCELED:
            payment_id = response_object.id
            try:
                # Ищем заказ по payment_id
                order = Order.objects.get(payment_id=payment_id)
                delete_order_with_canceled_payment.delay(order.id)
            except Order.DoesNotExist:
                logger.error(f"Order not found for payment ID: {payment_id}")
                return HttpResponse(status=400)

            except Exception as e:
                logger.error(f"Error updating order: {str(e)}")
                return HttpResponse(status=400)
        else:
            # Обработка ошибок
            return HttpResponse(status=400)  # Сообщаем кассе об ошибке

    except Exception:
        # Обработка ошибок
        return HttpResponse(status=400)  # Сообщаем кассе об ошибке

    return HttpResponse(status=200)  # Сообщаем кассе, что все хорошо
