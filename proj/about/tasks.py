from proj.celery import app
from proj.settings import EMAIL_HOST_USER, MANAGER_EMAIL
from django.core.mail import send_mail
import logging
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger('django')


@app.task
def send_mail_to_support_with_questions(user_pk, message):
    try:
        user = User.objects.get(pk=user_pk)
        username = user.username
        email = user.email
        last_name = user.last_name
        first_name = user.first_name
        patronymic = user.patronymic

        send_mail(
            f'Вопрос от пользователя по заказу {username}',
            f'От:\n{username} - {email}\n'
            f'{last_name} {first_name} {patronymic}\n'
            f'\n\n{message}',
            EMAIL_HOST_USER,
            [MANAGER_EMAIL],
            fail_silently=False,
        )

    except Exception as e:
        logger.error(f"Error sending email to support: {str(e)}")
