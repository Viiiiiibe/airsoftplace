from cart.models import Order
from proj.celery import app
from proj.settings import EMAIL_HOST_USER, MANAGER_EMAIL
from django.core.mail import send_mail
import logging
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger('django')


@app.task
def send_mail_to_support_task(order_id, ordr_shop, user_pk, message):
    try:
        user = User.objects.get(pk=user_pk)
        username = user.username
        email = user.email
        last_name = user.last_name
        first_name = user.first_name
        patronymic = user.patronymic

        send_mail(
            f'Обращение покупателя по заказу {order_id}',
            f'От:\n{username} - {email}\n'
            f'{last_name} {first_name} {patronymic}\n'
            f'Заказ: {order_id} из {ordr_shop}'
            f'\n\n{message}',
            EMAIL_HOST_USER,
            [MANAGER_EMAIL],
            fail_silently=False,
        )

    except Exception as e:
        logger.error(f"Error sending email to support: {str(e)}")


@app.task
def send_order_status_email(order_id):
    """
    Задача для отправки email с уведомлением об изменении статуса заказа
    """
    try:
        order = Order.objects.get(pk=order_id)

        send_mail(
            subject=f'Обновление статуса заказа {order.id}',
            message=f'статуса заказа #{order.id} изменен на {order.get_status_display()}',
            from_email=EMAIL_HOST_USER,
            recipient_list=[order.customer_email],
            fail_silently=False
        )
    except Exception as e:
        logger.error(f"Error in send_order_status_email: {str(e)}")
