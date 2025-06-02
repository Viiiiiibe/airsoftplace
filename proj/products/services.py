from django.core.cache import cache
from django.db.models import Q, Max, Min, Exists
from .models import Product, Category
from django.db.models import Subquery, OuterRef
from django.db.models import Avg, Count
from .utils import get_cached_items


def find_shop_categories(shop, category, cache_key):
    # пробуем взять из кэша
    result = cache.get(cache_key)
    if result is None:
        if category is None:
            # — корневая страница, без изменений —
            products = Product.objects.filter(shop=shop)
            # определяем корневые узлы, как раньше...
            root_ids = (
                Category.objects
                .filter(products__in=products)
                .distinct()
                .annotate(
                    root_id=Subquery(
                        Category.objects
                        .filter(tree_id=OuterRef('tree_id'), lft=1)
                        .values('id')[:1]
                    )
                )
                .values_list('root_id', flat=True)
            )
            qs = Category.objects.filter(id__in=root_ids).order_by('title')

        else:
            # — страница подкатегорий —
            # 1) выбираем прямых детей текущей категории:
            children = Category.objects.filter(parent=category)

            # 2) подзапрос: ищем товары в subtree каждого child:
            products_in_subtree = Product.objects.filter(
                shop=shop,
                category__tree_id=OuterRef('tree_id'),
                # любой потомок имеет lft >= child.lft и rght <= child.rght
                category__lft__gte=OuterRef('lft'),
                category__rght__lte=OuterRef('rght'),
            )

            # 3) аннотируем и фильтруем только тех children, у которых существует хоть один такой товар
            qs = (
                children
                .annotate(has_products=Exists(products_in_subtree))  # :contentReference[oaicite:1]{index=1}
                .filter(has_products=True)
                .order_by('title')
            )

        # приводим к списку и кэшируем
        result = list(qs)
        cache.set(cache_key, result, timeout=10 * 60)

    return result


def get_filtered_products_from_all(request, keyword):
    filters = {
        "product_type": "product_type__in",
        "compatibility": "compatibility__in",
        "thread_type": "thread_type__in",
        "mounting_type": "mounting_type__in",
        "imitation_of_a_shot": "imitation_of_a_shot__in",
        "laser_sight": "laser_sight__in",
        "weight": "weight__in",
        "principle_of_operation": "principle_of_operation__in",
        "diameter": "diameter__in",
    }

    queryset = Q(verified=True) & Q(show=True)
    base_query = Q(verified=True) & Q(show=True)
    if keyword:
        queryset &= Q(name__icontains=keyword)
        base_query &= Q(name__icontains=keyword)
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if min_price or max_price:
        price_range = Product.objects.filter(base_query).aggregate(Max("price"), Min("price"))
        queryset &= Q(price__range=(min_price or price_range["price__min"], max_price or price_range["price__max"]))

    min_length_get = request.GET.get("min_length", '')
    max_length_get = request.GET.get("max_length", '')

    if min_length_get or max_length_get:
        length_range = Product.objects.filter(base_query).aggregate(Max("length"), Min("length"))
        queryset &= Q(
            length__range=(min_price or length_range["length__min"], max_price or length_range["length__max"]))

    if request.GET.get("available", ''):
        queryset &= Q(items_left__gt=0)

    for param, field in filters.items():
        values = request.GET.getlist(param)
        if values:
            queryset &= Q(**{field: values})

    return Product.objects.filter(queryset).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True),
        order_count=Count('orderitems', distinct=True),
    ).order_by(request.GET.get("sort_by", "-pub_date"))


def get_all_products_filters(keyword):
    """Получает данные для фильтров с кешированием."""
    filter_fields = [
        ("price", Max, Min),
        "product_type",
        "compatibility",
        "thread_type",
        "mounting_type",
        "imitation_of_a_shot",
        "laser_sight",
        "weight",
        "principle_of_operation",
        ("length", Max, Min),
        "diameter",
    ]

    filters_data = {}
    base_query = Q(verified=True) & Q(show=True)
    if keyword:
        base_query &= Q(name__icontains=keyword)
    for field in filter_fields:
        if isinstance(field, tuple):
            field_name, max_func, min_func = field
            filters_data[f"{field_name}_data_for_filters"] = Product.objects.filter(base_query).aggregate(
                max_func(field_name), min_func(field_name))
        else:
            exclude_value = None
            filters_data[f"{field}_data_for_filters"] = Product.objects.filter(base_query).values(
                field).distinct().exclude(**{field: exclude_value})

    return filters_data


def get_category_filtered_products(category, request):
    filters = {
        "product_type": "product_type__in",
        "compatibility": "compatibility__in",
        "thread_type": "thread_type__in",
        "mounting_type": "mounting_type__in",
        "imitation_of_a_shot": "imitation_of_a_shot__in",
        "laser_sight": "laser_sight__in",
        "weight": "weight__in",
        "principle_of_operation": "principle_of_operation__in",
        "diameter": "diameter__in",
    }

    queryset = Q(category=category) & Q(verified=True) & Q(show=True)
    base_query = Q(category=category) & Q(verified=True) & Q(show=True)
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if min_price or max_price:
        price_range = get_cached_items(
            f"price_data_for_filters_in_{category.slug}_cache",
            Product.objects.filter(base_query).aggregate(Max("price"), Min("price"))
        )
        queryset &= Q(price__range=(min_price or price_range["price__min"], max_price or price_range["price__max"]))

    min_length_get = request.GET.get("min_length", '')
    max_length_get = request.GET.get("max_length", '')

    if min_length_get or max_length_get:
        length_range = get_cached_items(
            f"length_data_for_filters_in_{category.slug}_cache",
            Product.objects.filter(base_query).aggregate(Max("length"), Min("length"))
        )
        queryset &= Q(
            length__range=(min_price or length_range["length__min"], max_price or length_range["length__max"]))

    if request.GET.get("available", ''):
        queryset &= Q(items_left__gt=0)

    for param, field in filters.items():
        values = request.GET.getlist(param)
        if values:
            queryset &= Q(**{field: values})

    return Product.objects.filter(queryset).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True),
        order_count=Count('orderitems', distinct=True),
    ).order_by(request.GET.get("sort_by", "-pub_date"))


def get_category_filters(category):
    """Получает данные для фильтров по категории с кешированием."""
    filter_fields = [
        ("price", Max, Min),
        "product_type",
        "compatibility",
        "thread_type",
        "mounting_type",
        "imitation_of_a_shot",
        "laser_sight",
        "weight",
        "principle_of_operation",
        ("length", Max, Min),
        "diameter",
    ]

    filters_data = {}
    base_query = Q(category=category) & Q(verified=True) & Q(show=True)
    for field in filter_fields:
        if isinstance(field, tuple):
            field_name, max_func, min_func = field
            filters_data[f"{field_name}_data_for_filters"] = get_cached_items(
                f"{field_name}_data_for_filters_in_{category.slug}_cache",
                Product.objects.filter(base_query).aggregate(max_func(field_name), min_func(field_name))
            )
        else:
            exclude_value = None
            filters_data[f"{field}_data_for_filters"] = get_cached_items(
                f"{field}_data_for_filters_in_{category.slug}_cache",
                Product.objects.filter(base_query).values(field).distinct().exclude(**{field: exclude_value})
            )

    return filters_data


def get_shop_filtered_products(category, shop, request):
    filters = {
        "product_type": "product_type__in",
        "compatibility": "compatibility__in",
        "thread_type": "thread_type__in",
        "mounting_type": "mounting_type__in",
        "imitation_of_a_shot": "imitation_of_a_shot__in",
        "laser_sight": "laser_sight__in",
        "weight": "weight__in",
        "principle_of_operation": "principle_of_operation__in",
        "diameter": "diameter__in",
    }

    queryset = Q(category=category) & Q(shop=shop) & Q(verified=True) & Q(show=True)
    base_query = Q(category=category) & Q(shop=shop) & Q(verified=True) & Q(show=True)
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if min_price or max_price:
        price_range = get_cached_items(
            f"shop_{shop.slug}_price_data_for_filters_in_{category.slug}_cache",
            Product.objects.filter(base_query).aggregate(Max("price"), Min("price"))
        )
        queryset &= Q(price__range=(min_price or price_range["price__min"], max_price or price_range["price__max"]))

    min_length_get = request.GET.get("min_length", '')
    max_length_get = request.GET.get("max_length", '')

    if min_length_get or max_length_get:
        length_range = get_cached_items(
            f"shop_{shop.slug}_length_data_for_filters_in_{category.slug}_cache",
            Product.objects.filter(base_query).aggregate(Max("length"), Min("length"))
        )
        queryset &= Q(
            length__range=(min_price or length_range["length__min"], max_price or length_range["length__max"]))

    if request.GET.get("available", ''):
        queryset &= Q(items_left__gt=0)

    for param, field in filters.items():
        values = request.GET.getlist(param)
        if values:
            queryset &= Q(**{field: values})

    return Product.objects.filter(queryset).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True),
        order_count=Count('orderitems', distinct=True),
    ).order_by(request.GET.get("sort_by", "-pub_date"))


def get_shop_category_filters(category, shop):
    """Получает данные для фильтров по категории с кешированием."""
    filter_fields = [
        ("price", Max, Min),
        "product_type",
        "compatibility",
        "thread_type",
        "mounting_type",
        "imitation_of_a_shot",
        "laser_sight",
        "weight",
        "principle_of_operation",
        ("length", Max, Min),
        "diameter",
    ]

    filters_data = {}
    base_query = Q(category=category) & Q(shop=shop) & Q(verified=True) & Q(show=True)
    for field in filter_fields:
        if isinstance(field, tuple):
            field_name, max_func, min_func = field
            filters_data[f"{field_name}_data_for_filters"] = get_cached_items(
                f"shop_{shop.slug}_{field_name}_data_for_filters_in_{category.slug}_cache",
                Product.objects.filter(base_query).aggregate(max_func(field_name), min_func(field_name))
            )
        else:
            # Если поле числовое, исключаем `None`, а не `""`
            exclude_value = None
            filters_data[f"{field}_data_for_filters"] = get_cached_items(
                f"shop_{shop.slug}_{field}_data_for_filters_in_{category.slug}_cache",
                Product.objects.filter(base_query).values(field).distinct().exclude(**{field: exclude_value})
            )

    return filters_data
