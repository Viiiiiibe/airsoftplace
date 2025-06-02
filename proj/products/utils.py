from django.core.cache import cache
from django.shortcuts import get_object_or_404

from products.models import Shop

CACHE_TIMEOUT = 10 * 60  # 10 минут


def get_cached_items(key, queryset):
    return cache.get_or_set(key, queryset, CACHE_TIMEOUT)


def get_product_text(product):
    """
    Собирает текстовое описание товара из его характеристик
    """
    # Получаем список названий категорий, если поле category – ManyToManyField
    categories = " ".join(cat.title for cat in product.category.all())
    brand = product.brand or ""
    product_type = product.product_type or ""
    compatibility = product.compatibility or ""
    thread_type = product.thread_type or ""
    mounting_type = product.mounting_type or ""
    principle_of_operation = product.principle_of_operation or ""
    return (f"{product.name} {categories} {brand} {product_type} {compatibility} {thread_type} {mounting_type} "
            f"{principle_of_operation}")


def set_shop_info_cache(shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug)
    owner = shop.sellers.first()
    if shop.type in ('self-employed', 'individual_entrepreneur'):
        if owner:
            fio = ' '.join(filter(None, [owner.last_name, owner.first_name, owner.patronymic]))
        else:
            fio = ""
        if shop.type == 'individual_entrepreneur':
            extra = []
            if shop.INN:
                extra.append(f'ИНН: {shop.INN}')
            if shop.OGRNIP:
                extra.append(f'ОГРНИП: {shop.OGRNIP}')
            cache.set(f"shop_{shop_slug}_info_cache",
                      f'{shop.get_type_display()} ' + fio + (', ' + ', '.join(extra) if extra else ''), 60 * 60 * 24)
        else:
            cache.set(f"shop_{shop_slug}_info_cache", f'{shop.get_type_display()} ' + fio, 60 * 60 * 24)
    elif shop.type == 'legal_person':
        cache.set(f"shop_{shop_slug}_info_cache", f'{shop.get_type_display()} {shop.title}, ОГРН: {shop.OGRN}',
                  60 * 60 * 24)
    else:
        cache.set(f"shop_{shop_slug}_info_cache", shop.title, 60 * 60 * 24)
