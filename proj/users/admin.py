from django.contrib import admin
from .models import CustomUser
from .forms import RegisterForm, CustomUserChangeForm


class CustomUserAdmin(admin.ModelAdmin):
    add_form = RegisterForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ['email', 'username', 'shop']


admin.site.register(CustomUser, CustomUserAdmin)
