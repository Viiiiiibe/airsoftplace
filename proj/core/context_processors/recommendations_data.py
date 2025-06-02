from django.db.models import Q, Avg, Count
from django.core.cache import cache
from products.models import Product
from products.tasks import find_recommended_products_for_user


def get_product_text(product):
    """
    Собирает текстовое описание товара из его имени, описания и категорий.
    """
    # Получаем список названий категорий, если поле category – ManyToManyField
    categories = product.category.all()
    cat_text = " ".join([cat.title for cat in categories])
    description = product.description if product.description else ""
    return f"{product.name} {cat_text} {description}"


def recommendations_data(request):
    queryset = Q(verified=True) & Q(show=True)

    if request.user.is_authenticated:
        if cache.get(f"recommended_products_cache_user_{request.user.pk}"):
            return {'recommended_products': cache.get(f"recommended_products_cache_user_{request.user.pk}")}
        # Иначе: собираем из сессии до 10 последних просмотров
        viewed_ids = request.session.get('recently_viewed', [])  # список ID, max len=10

        # Запускаем асинхронную задачу: передаём user_pk и viewed_ids
        find_recommended_products_for_user.delay(request.user.pk, viewed_ids)
    # Если пользователь не авторизован или не взаимодействовал с товарами
    # или идет ожидание задачи используем популярные товары
    recommended_products = cache.get_or_set("recommended_products_cache", Product.objects.filter(queryset).annotate(
                                        avg_rating=Avg('reviews__rating'),
                                        review_count=Count('reviews', distinct=True),
                                        order_count=Count('orderitems', distinct=True),
                                    ).filter(
                                        avg_rating__gte=4  # Только товары со средним рейтингом >= 4
                                    ).order_by('-order_count')[:10], 10 * 60)
    return {'recommended_products': recommended_products}
