from django.shortcuts import render
from .tasks import send_mail_to_support_with_questions


def our_team(request):
    return render(request, 'about/our_team.html')


def contacts(request):
    if request.method == 'POST' and request.user.is_authenticated:
        user_pk = request.user.pk
        message = request.POST.get("message", None)
        if message:
            # Отправка письма
            send_mail_to_support_with_questions.delay(user_pk, message)
    return render(request, 'about/contacts.html')


def faq(request):
    return render(request, 'about/faq.html')
