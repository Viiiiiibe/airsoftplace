from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django import forms
from products.models import Shop
from .models import CustomUser
from products.models import Product, Category

User = get_user_model()


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'username', 'last_name', 'first_name', 'patronymic', 'email',
                  'phone_number', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Адрес электронной почты уже привязан к аккаунту или содержит ошибку")

        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Email / Username')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        # fields = "__all__"
        fields = ('username', 'email', 'last_name', 'first_name', 'patronymic', 'email', 'phone_number',
                  'shop', 'is_active', 'is_superuser', 'is_staff', 'groups', 'user_permissions', 'date_joined',
                  'last_login',)


class CustomUserChangeFromUserInterfaceForm(UserChangeForm):
    class Meta:
        model = CustomUser
        # fields = "__all__"
        fields = ('username', 'email', 'last_name', 'first_name', 'patronymic', 'email', 'phone_number')


class ShopRegistrationForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = ['title', 'slug', 'type', 'address', 'INN', 'OGRNIP', 'OGRN', 'payment_account', 'BIC']
        labels = {
            'title': 'Название магазина',
            'slug': 'URL-адрес магазина',
            'type': 'Тип юридического лица',
            'address': 'Адрес регистрации',
            'INN': 'ИНН',
            'OGRNIP': 'ОГРНИП',
            'OGRN': 'ОГРН',
            'payment_account': 'Расчётный счёт',
            'BIC': 'БИК',
        }
        help_texts = {
            'slug': 'Уникальный идентификатор для URL вашего магазина',
            'address': 'Для всех. Страна, область, город, индекс, улица, дом',
            'INN': 'Для всех',
            'OGRNIP': 'Для ИП',
            'OGRN': 'Для юрлиц',
            'payment_account': 'Только банка РФ'
        }

    # def clean_slug(self):
    #     slug = self.cleaned_data.get('slug')
    #     if Shop.objects.filter(slug=slug).exists():
    #         raise forms.ValidationError("Этот URL уже занят, выберите другой")
    #     return slug


class ProductForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        leaf_categories = Category.objects.filter(children__isnull=True)
        self.fields['category'].queryset = leaf_categories

        # Инициализация для редактирования существующего товара
        if self.instance.pk:
            self.fields['category'].initial = self.instance.category.all()

        # Формирование breadcrumbs_data
        self.breadcrumbs_data = {
            str(cat.id): {
                'name': cat.title,
                'path': cat.get_ancestors(include_self=True)
            } for cat in leaf_categories
        }

    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Категории"
    )

    class Meta:
        model = Product
        fields = '__all__'
        exclude = ['verified', 'shop', 'pub_date']


class ProductUpdateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['items_left', 'show']

    widgets = {
        'show': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    }
