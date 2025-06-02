from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from products.models import Shop


class CustomUser(AbstractUser):
    patronymic = models.CharField(blank=True, null=True, max_length=150, verbose_name='Отчество')
    email = models.EmailField(_('email address'), unique=True)
    phone_number = PhoneNumberField(blank=True, null=True, unique=True, verbose_name='Тлефон')
    shop = models.ForeignKey(
        Shop,
        related_name='sellers',
        verbose_name='Магазин',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
