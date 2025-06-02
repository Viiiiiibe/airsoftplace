from django.test import Client, TestCase
from django.urls import reverse
from ..models import Product, Category, Shop


class ContextTestsForPagesWithProducts(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        """Подготавливаем тестовые данные."""
        # Создаем категории
        cls.cat1 = Category.objects.create(pk=1, title='Категория номер 1', slug='category1')
        cls.cat2 = Category.objects.create(pk=2, title='Категория номер 2', slug='category2')
        cls.cat3 = Category.objects.create(pk=3, title='Категория номер 3', slug='category3', parent=cls.cat1)
        cls.cat4 = Category.objects.create(pk=4, title='Категория номер 4', slug='category4', parent=cls.cat1)

        cls.shop1 = Shop.objects.create(pk=1, title='Магазин номер 1', slug='shop1')

        # Создадим товары 1 до 11
        for i in range(1, 12):
            prod = Product.objects.create(pk=i, name=f'Товар номер {i}', price=i, items_left=i,
                                          shop=Shop.objects.get(pk=1))
            prod.category.set(Category.objects.filter(pk=4))

    def setUp(self):
        """Вызывается перед каждым тестом."""
        self.guest_client = Client()

    def test_index_show_correct_context(self):
        """Главная страница содержит новинки и рекомендуемые товары."""
        response = self.client.get(reverse('index'))

        # Проверяем, что список товаров не пуст
        self.assertIn('products', response.context, "Контекст не содержит 'products'")
        self.assertGreaterEqual(len(response.context['products']), 10,
                                "Недостаточно товаров в products")

        # Проверка 10 последних товаров (новинки)
        for i, product in enumerate(response.context['products'][:10], start=1):
            with self.subTest(i=i):
                self.assertEqual(product.name, f'Товар номер {12 - i}')

    def test_all_products_show_correct_context(self):
        """Страница всех товаров содержит корректный список товаров и рекомендуемые товары."""
        response = self.client.get(reverse('all_products'))

        # Проверяем, что список товаров не пуст
        self.assertIn('page_obj', response.context, "Контекст не содержит 'page_obj'")
        self.assertGreaterEqual(len(response.context['page_obj']), 11,
                                "Недостаточно товаров в page_obj")

        # Проверка последних товаров
        for i, product in enumerate(response.context['page_obj'], start=1):
            with self.subTest(i=i):
                self.assertEqual(product.name, f'Товар номер {12 - i}')

    def test_all_products_with_keyword_show_correct_context(self):
        """Проверяет, что поиск по ключевому слову возвращает корректный товар и рекомендуемые товары."""
        url = f"{reverse('all_products')}?q=11"
        response = self.guest_client.get(url)

        # Проверяем, что список товаров не пуст
        self.assertIn('page_obj', response.context, "Контекст не содержит 'page_obj'")
        self.assertTrue(response.context['page_obj'], "Список товаров пуст")

        # Проверяем товар, найденный по запросу "11"
        product_name = response.context['page_obj'][0].name
        self.assertEqual(product_name, 'Товар номер 11')

    def test_categories_show_correct_context(self):
        """Проверяет, что список категорий передается в шаблон правильно."""
        response = self.guest_client.get(reverse('categories'))
        # Проверяем, что список категорий не пуст
        self.assertIn('categories', response.context, "Контекст не содержит 'categories'")
        self.assertGreaterEqual(len(response.context['categories']), 2, "Недостаточно категорий")
        # Проверяем названия категорий
        cat1 = response.context['categories'][0].title
        cat2 = response.context['categories'][1].title
        self.assertEqual(cat1, 'Категория номер 1')
        self.assertEqual(cat2, 'Категория номер 2')

    def test_subcategories_show_correct_context(self):
        """Проверяет, что список подкатегорий передается в шаблон правильно."""
        response = self.guest_client.get(reverse('subcategories', kwargs={'slug': 'category1'}))
        # Проверяем, что список подкатегорий не пуст
        self.assertIn('subcategories', response.context, "Контекст не содержит 'subcategories'")
        self.assertGreaterEqual(len(response.context['subcategories']), 2, "Недостаточно подкатегорий")
        # Проверяем названия подкатегорий
        subcat1 = response.context['subcategories'][0].title
        subcat2 = response.context['subcategories'][1].title
        self.assertEqual(subcat1, 'Категория номер 3')
        self.assertEqual(subcat2, 'Категория номер 4')

    def test_category_products_show_correct_context(self):
        """Проверяет, что страница категории отображает товары в правильном порядке и рекомендуемые товары."""
        response = self.guest_client.get(reverse('category_products', kwargs={'slug': 'category4'}))

        # Проверяем, что 'page_obj' есть в контексте и содержит товары
        self.assertIn('page_obj', response.context, "Контекст не содержит 'page_obj'")
        self.assertEqual(len(response.context['page_obj']), 11, "Ожидается 11 товаров в категории")

        # Проверяем, что товары отсортированы по убыванию (от 11 до 1)
        expected_product_names = [f'Товар номер {i}' for i in range(11, 0, -1)]
        actual_product_names = [product.name for product in response.context['page_obj']]
        self.assertEqual(actual_product_names, expected_product_names, "Товары отсортированы неверно")

    def test_product_detail_show_correct_context(self):
        """Проверяет, что страница товара отображает правильный продукт и рекомендуемые товары."""
        response = self.guest_client.get(reverse('product_detail', kwargs={'product_id': 1}))

        # Проверяем, что 'product' есть в контексте
        self.assertIn('product', response.context, "Контекст не содержит 'product'")

        # Проверяем данные конкретного товара
        product = response.context['product']
        self.assertEqual(product.name, 'Товар номер 1')
        self.assertEqual(product.price, 1)


class ProductFiltersInCategoryProductsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        """Подготавливаем тестовые данные."""
        # Создаем категории
        cls.cat1 = Category.objects.create(pk=1, title='Категория номер 1', slug='category1')

        # Создадим товары 1 до 12
        for i in range(1, 13):
            prod = Product.objects.create(pk=i, name=f'Товар номер {i}', price=i, items_left=i)
            prod.category.set(Category.objects.filter(pk=1))

        filters = {
            1: {"product_type": "Тип 2"},
            2: {"product_type": "Тип 1"},
            3: {"compatibility": "Ak-47"},
            4: {"thread_type": "4x4"},
            5: {"mounting_type": "На скотч"},
            6: {"imitation_of_a_shot": True},
            7: {"laser_sight": True},
            8: {"weight": 4.4},
            9: {"principle_of_operation": "С Божьей помощью"},
            10: {"length": 4},
            11: {"diameter": 7.7},
        }
        for pk, update_data in filters.items():
            Product.objects.filter(pk=pk).update(**update_data)

        # # Временный print для отладки
        # for product in Product.objects.all():
        #     print(
        #         f'ID: {product.pk}, Name: {product.name}, '
        #         f'Category: {product.category.all()}, Filters: {vars(product)}'
        #     )

    def setUp(self):
        self.guest_client = Client()

    def test_filters(self):
        """Проверка фильтров товаров в категории."""
        filters = {
            "max_price": "1",
            "product_type": "Тип 1",
            "compatibility": "Ak-47",
            "thread_type": "4x4",
            "mounting_type": "На скотч",
            "imitation_of_a_shot": "True",
            "laser_sight": "True",
            "weight": "4.4",
            "principle_of_operation": "С Божьей помощью",
            "min_length": "4",
            "diameter": "7.7",
        }

        for filter_name, value in filters.items():
            with self.subTest(filter=filter_name, value=value):
                url = '{url}?{filter}={value}'.format(
                    url=reverse('category_products', kwargs={'slug': 'category1'}),
                    filter=filter_name, value=value
                )

                response = self.client.get(url)

                # print(f"testing filter {filter_name}={value}")

                # Проверяем, что фильтр возвращает хотя бы один товар
                self.assertGreater(
                    len(response.context['page_obj']),
                    0,
                    f"Фильтр {filter_name}={value} не вернул ни одного товара!"
                )

                expected_product = 'Товар номер ' + str(list(filters.keys()).index(filter_name) + 1)

                # Проверяем, что первый товар в выдаче соответствует ожидаемому
                self.assertEqual(response.context['page_obj'][0].name, expected_product)
