from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from products.models import Shop, Product
from decimal import Decimal
from proj.settings import AUTH_USER_MODEL

User = AUTH_USER_MODEL


# User = get_user_model()


class ShippingAddress(models.Model):
    country = models.CharField(max_length=100, verbose_name='Страна', default='Россия')
    region = models.CharField(max_length=150, verbose_name='Область')
    city = models.CharField(max_length=150, verbose_name='Населенный пункт')
    street = models.CharField(blank=True, null=True, max_length=150, verbose_name='Улица')
    house = models.CharField(blank=True, null=True, max_length=150, verbose_name='Дом')
    flat = models.CharField(blank=True, null=True, max_length=150, verbose_name='Квартира')
    entrance = models.CharField(blank=True, null=True, max_length=150, verbose_name='Подъезд')
    floor = models.CharField(blank=True, null=True, max_length=150, verbose_name='Этаж')
    intercom = models.CharField(blank=True, null=True, max_length=150, verbose_name='Домофон')
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Пользователь')

    def __str__(self):
        return ("Адрес " + str(self.pk) + ", пользователь " + str(self.user) + ", " + str(self.country) + ", " +
                str(self.region) + " обл., " + str(self.city) + ", ул. " + str(self.street) + ", д. " +
                str(self.house) + ", кв. " + str(self.flat) + ", этаж " + str(self.floor) + ", домофон " +
                str(self.intercom))

    class Meta:
        verbose_name = "Адрес доставки"
        verbose_name_plural = "Адреса доставки"
        ordering = ['-pk']


class Order(models.Model):
    STATUS_OPTIONS = (
        ('awaiting_payment', 'Ожидает оплаты'),
        ('in_assembly', 'В сборке'),
        ('transferred_to_delivery', 'Передаётся в доставку'),
        ('on_the_way', 'В пути'),
        ('awaiting_receipt', 'Ожидает получения'),
        ('received', 'Получен '),
        ('canceled', 'Отменен')
    )
    DELIVERY_METHOD_OPTIONS = (
        ('pick-up_point', 'Пункт выдачи '),
        ('by_courier', 'Курьером')
    )
    shop = models.ForeignKey(
        Shop,
        related_name='orders',
        verbose_name='Магазин',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
    customer_last_name = models.CharField(max_length=150, verbose_name='Фамилия заказчика')
    customer_first_name = models.CharField(max_length=150, verbose_name='Имя заказчика')
    customer_patronymic = models.CharField(blank=True, null=True, max_length=150, verbose_name='Отчество заказчика')
    customer_email = models.EmailField(verbose_name='Почта заказчика')
    customer_phone = PhoneNumberField(verbose_name='Тлефон заказчика')
    delivery_method = models.CharField(choices=DELIVERY_METHOD_OPTIONS, default='pick-up_point', max_length=150,
                                       verbose_name='Способ доставки')
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    status = models.CharField(max_length=150, choices=STATUS_OPTIONS, default='awaiting_payment',
                              verbose_name='Статус заказа')
    shipping_address = models.ForeignKey(
        ShippingAddress,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        verbose_name='Адрес доставки'
    )
    amount = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Сумма')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')
    updated = models.DateTimeField(auto_now=True, verbose_name='Время обновления')
    paid = models.BooleanField(default=False, verbose_name='Оплачен')
    payment_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='ID платежа')

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created']
        indexes = [
            models.Index(fields=['-created']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(
                amount__gte=0), name='amount_gte_0'),
        ]

    def __str__(self):
        return "Заказ " + str(self.pk)

    def get_total_cost_before_discount(self):
        return sum(item.get_cost() for item in self.items.all())

    @property
    def get_discount(self):
        if (total_cost := self.get_total_cost_before_discount()) and self.discount:
            return total_cost * (self.discount / Decimal(100))
        return Decimal(0)

    def get_total_cost(self):
        total_cost = self.get_total_cost_before_discount()
        return total_cost - self.get_discount


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, blank=True, null=True, related_name='items', verbose_name='Заказ')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, blank=True, null=True, related_name='orderitems', verbose_name='Товар')
    price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Цена')
    quantity = models.IntegerField(default=1, verbose_name='Количество')

    class Meta:
        verbose_name = "Заказанный товар"
        verbose_name_plural = "Заказанные товары"
        ordering = ['-pk']
        constraints = [
            models.CheckConstraint(check=models.Q(
                quantity__gt=0), name='quantity_gte_0'),
        ]

    def __str__(self):
        return "Заказанный товар " + str(self.pk)

    def get_cost(self):
        return self.price * self.quantity

    @property
    def total_cost(self):
        return self.price * self.quantity

    @classmethod
    def get_total_quantity_for_product(cls, product):
        return cls.objects.filter(product=product).aggregate(total_quantity=models.Sum('quantity'))[
            'total_quantity'] or 0

    @staticmethod
    def get_average_price():
        return OrderItem.objects.aggregate(average_price=models.Avg('price'))['average_price']


class StoreSalesReport(models.Model):
    shop = models.ForeignKey(
        Shop,
        related_name='store_sales_reports',
        verbose_name='Магазин',
        blank=False, null=True,
        on_delete=models.CASCADE
    )
    start_date = models.DateField(verbose_name="С")
    end_date = models.DateField(verbose_name="По")
    revenue = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Выручка"
    )
    orders = models.ManyToManyField(
        Order,
        related_name='store_sales_reports',
        verbose_name='Заказы',
        blank=True, null=True,
    )
    category_performance = models.JSONField(
        verbose_name="Продажи по категориям",
        blank=True,
        null=True,
        help_text="Словарь с ID категории и объемами продаж"
    )
    products_performance = models.JSONField(
        verbose_name="Продажи по товарам",
        blank=True,
        null=True,
        help_text="Словарь с ID товаров и объемами продаж"
    )

    class Meta:
        verbose_name = "Отчет о продажах магазина"
        verbose_name_plural = "Отчеты о продажах магазина"
