from django.db import models
from mptt.models import MPTTModel, TreeForeignKey, TreeManyToManyField
import random
import string
from django.utils.text import slugify
from proj.settings import AUTH_USER_MODEL

User = AUTH_USER_MODEL


class Shop(models.Model):
    TYPE_OPTIONS = (
        ('self-employed', 'самозанятый'),
        ('individual_entrepreneur', 'Индивидуальный предприниматель'),
        ('legal_person', 'юрлицо')
    )
    title = models.CharField(verbose_name='Название', max_length=200)
    slug = models.SlugField(verbose_name='Название в URL', max_length=200, unique=True)
    type = models.CharField(choices=TYPE_OPTIONS, default='self-employed', max_length=150, verbose_name='Тип')
    address = models.CharField('Адрес регистрации', max_length=250,
                               help_text="Для всех. Страна, область, город, индекс, улица, дом"
                               )
    INN = models.CharField(verbose_name='ИНН', max_length=12, help_text="Для всех")
    OGRNIP = models.CharField(verbose_name='ОГРНИП', help_text="Для ИП", max_length=15, blank=True, null=True, )
    OGRN = models.CharField(verbose_name='ОГРН', help_text="Для юрлиц", max_length=15, blank=True, null=True, )
    payment_account = models.CharField(verbose_name='Расчётный счёт', help_text="Только банка РФ", max_length=20)
    BIC = models.CharField(verbose_name='БИК', max_length=9)
    verified = models.BooleanField("Верифицированный", default=False)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'


class Category(MPTTModel):
    title = models.CharField(verbose_name='Название', max_length=200)
    slug = models.SlugField(verbose_name='Название в URL', max_length=200, unique=True)
    parent = TreeForeignKey('self', verbose_name='Родительская категория', null=True, blank=True,
                            related_name='children', on_delete=models.CASCADE)
    image = models.ImageField(
        'Картинка 896x485 для показа в списках',
        upload_to='category_img/',
        default='/category_img/default_category_img.png'
    )

    def __str__(self):
        return f'{self.title}'

    @staticmethod
    def _rand_slug():
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(3))

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self._rand_slug() + '-pickBetter' + self.title)
        super(Category, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class Product(models.Model):
    # Общие поля
    name = models.CharField(verbose_name='Название', max_length=250)
    category = TreeManyToManyField(
        'Category',
        blank=False,
        null=False,
        related_name='products',
        verbose_name='Категория',
    )
    shop = models.ForeignKey(
        Shop,
        related_name='products',
        verbose_name='Магазин',
        blank=False, null=True,
        on_delete=models.CASCADE
    )
    description = models.TextField(verbose_name='Описание', blank=True, null=True)
    price = models.FloatField(verbose_name='Цена в рублях', )
    items_left = models.IntegerField(verbose_name='Осталось единиц товара')
    pub_date = models.DateTimeField(verbose_name='Дата добавления', auto_now_add=True)
    image1 = models.ImageField(
        'Изображение 1 для страницы продукта',
        upload_to='product_img/',
        default='/product_img/default_product_detail_img.png',
        help_text="Минимальный рекомендуемый размер - 536x639"
    )
    image2 = models.ImageField(
        'Изображение 2 для страницы продукта',
        upload_to='product_img/',
        blank=True, null=True,
        help_text="Минимальный рекомендуемый размер - 536x639"
    )
    image3 = models.ImageField(
        'Изображение 3 для страницы продукта',
        upload_to='product_img/',
        blank=True, null=True,
        help_text="Минимальный рекомендуемый размер - 536x639"
    )
    image4 = models.ImageField(
        'Изображение 4 для страницы продукта',
        upload_to='product_img/',
        blank=True, null=True,
        help_text="Минимальный рекомендуемый размер - 536x639"
    )
    image5 = models.ImageField(
        'Изображение для описания на странице продукта',
        upload_to='product_img/',
        blank=True, null=True,
        help_text="Минимальный рекомендуемый размер - 1140x760"
    )
    image6 = models.ImageField(
        'Изображение для показа в списках',
        upload_to='product_img/',
        default='/product_img/default_products_list_img.png',
        help_text="Минимальный рекомендуемый размер - 433x516"
    )
    link_to_a_video = models.CharField(verbose_name='Ссылка на видео', blank=True, null=True, max_length=250)
    brand = models.CharField("Бренд", max_length=250, blank=True, null=True)
    show = models.BooleanField("Показывать", default=True)
    verified = models.BooleanField("Верифицированный", default=False)

    # Поля для дополнительных характеристик
    product_type = models.CharField('Тип товара', blank=True, null=True, max_length=250,
                                    help_text="Рекомендуется для ДТК, глушителей, прикладов, фонарей, масок, очков, "
                                              "шаров, экипировки, hop-up, стволиков, прикладов")
    compatibility = models.CharField('Совместимость', blank=True, null=True, max_length=250,
                                     help_text="Рекомендуется для прикладов, магазинов, триггеров, цевья, стволиков")
    thread_type = models.CharField('Тип резьбы', blank=True, null=True, max_length=250,
                                   help_text="Рекомендуется для ДТК, глушителей, трассерных насадок")
    mounting_type = models.CharField('Тип крепления', blank=True, null=True, max_length=250,
                                     help_text="Рекомендуется для тактических рукояток")
    imitation_of_a_shot = models.BooleanField('Имитация выстрела', blank=True, null=True,
                                              help_text="Рекомендуется для трассерных насадок")
    laser_sight = models.BooleanField('С ЛЦУ', blank=True, null=True,
                                      help_text="Рекомендуется для фонарей")
    weight = models.FloatField('Вес в гр.', blank=True, null=True,
                               help_text="Рекомендуется для шаров")
    principle_of_operation = models.CharField('Принцип действия', blank=True, null=True, max_length=250,
                                              help_text="Рекомендуется для автоматов, винтовок и пистолетов")
    length = models.IntegerField('Длина в мм', blank=True, null=True,
                                 help_text="Рекомендуется для стволиков")
    diameter = models.FloatField('Диаметр в мм', blank=True, null=True,
                                 help_text="Рекомендуется для стволиков")

    # Поля для доставки
    warehouse_city = models.CharField("Город Склада", max_length=250)
    shipping_width = models.FloatField("Ширина при доставке в см", max_length=50)
    shipping_length = models.FloatField("Длина при доставке в см", max_length=50)
    shipping_height = models.FloatField("Высота при доставке в см", max_length=50)
    shipping_weight = models.FloatField("Вес при доставке в кг", max_length=50)

    def __str__(self):
        return f'{self.name}'

    def categories(self): return ",".join([str(p) for p in self.category.all()])

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'


class Review(models.Model):
    RATING_OPTIONS = (
        (1, '★'),
        (2, '★★'),
        (3, '★★★'),
        (4, '★★★★'),
        (5, '★★★★★'),
    )
    text = models.TextField(verbose_name='Текст', blank=True, null=True)
    rating = models.IntegerField(choices=RATING_OPTIONS, default='5', verbose_name='Оценка')
    image = models.ImageField(
        'Фото',
        upload_to='reviews_img/',
        blank=True,
        null=True
    )
    product = models.ForeignKey(
        Product,
        related_name='reviews',
        verbose_name='Товар',
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User,
        related_name='reviews',
        verbose_name='Пользователь',
        on_delete=models.CASCADE
    )
    pub_date = models.DateTimeField(verbose_name='Дата добавления', auto_now_add=True)
    show = models.BooleanField("Показывать", default=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
