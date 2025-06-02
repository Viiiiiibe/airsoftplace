from django import forms
from .models import Order
from phonenumber_field.formfields import PhoneNumberField


class MakingAnOrderForm(forms.ModelForm):
    customer_last_name = forms.CharField
    customer_first_name = forms.CharField
    customer_patronymic = forms.CharField
    customer_email = forms.EmailField
    customer_phone = PhoneNumberField

    class Meta:
        model = Order
        # fields = "__all__"
        fields = ('customer_last_name', 'customer_first_name', 'customer_patronymic', 'customer_email',
                  'customer_phone',)
