from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from cart.cart import Cart
from .models import Product, Category, Shop, Review
from .services import get_category_filtered_products, get_category_filters, \
    get_shop_category_filters, get_shop_filtered_products, find_shop_categories, get_all_products_filters, \
    get_filtered_products_from_all
from .utils import get_cached_items, set_shop_info_cache
from django.db.models import Q
from .forms import ReviewForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from cart.models import OrderItem
from django.db.models import Avg, Count
from django.urls import reverse
from django.core.cache import cache


def index(request):
    queryset = Q(verified=True) & Q(show=True)
    products = get_cached_items("10_popular_products_cache",
                                Product.objects.filter(queryset).annotate(
                                    avg_rating=Avg('reviews__rating'),
                                    review_count=Count('reviews', distinct=True),
                                    order_count=Count('orderitems', distinct=True),
                                ).filter(
                                    avg_rating__gte=4  # Только товары со средним рейтингом >= 4
                                ).order_by('-order_count')[:10])
    context = {"products": products}
    return render(request, "products/index.html", context)


def all_products(request):
    keyword = request.GET.get("q")
    filters_data = get_all_products_filters(keyword)
    products = get_filtered_products_from_all(request, keyword)

    paginator = Paginator(products, request.GET.get("prod_count", 24))
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "keyword": keyword,
        "page_obj": page_obj,
        "sort_parameter": request.GET.get("sort_by", "-pub_date"),
        **filters_data
    }
    return render(request, "products/all_products.html", context)


def categories(request):
    categories = get_cached_items("categories_without_parents_cache",
                                  Category.objects.filter(parent=None).order_by("title"))
    context = {"categories": categories}
    return render(request, "products/categories.html", context)


def subcategories(request, slug):
    category = get_object_or_404(Category, slug=slug)
    subcategories = get_cached_items(f"{slug}_subcategories_cache", Category.objects.filter(parent=category))
    context = {"subcategories": subcategories, "category": category}
    return render(request, "products/subcategories.html", context)


def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)

    filters_data = get_category_filters(category)
    products = get_category_filtered_products(category, request)

    paginator = Paginator(products, request.GET.get("prod_count", 24))
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {"category": category, "page_obj": page_obj, "sort_parameter": request.GET.get("sort_by", "-pub_date"),
               **filters_data}
    return render(request, "products/category_list.html", context)


def shops(request):
    shops = get_cached_items("shops_cache",
                             Shop.objects.filter(verified=True).order_by("title"))
    paginator = Paginator(shops, 24)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {"shops": page_obj}
    return render(request, "products/shops.html", context)


def shop_categories(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug)
    cache_key = f"shop_{shop_slug}_categories_cache"

    root_categories = find_shop_categories(shop, None, cache_key)

    if not cache.get(f"shop_{shop_slug}_info_cache"):
        set_shop_info_cache(shop_slug)
    shop_info = cache.get(f"shop_{shop_slug}_info_cache")

    context = {
        "categories": root_categories,
        "shop": shop,
        "shop_info": shop_info,
    }
    return render(request, "products/shop_categories.html", context)


def shop_subcategories(request, shop_slug, slug):
    shop = get_object_or_404(Shop, slug=shop_slug)
    category = get_object_or_404(Category, slug=slug)
    cache_key = f"shop_{shop_slug}_category_{slug}_subcategories_cache"

    root_categories = find_shop_categories(shop, category, cache_key)

    if not cache.get(f"shop_{shop_slug}_info_cache"):
        set_shop_info_cache(shop_slug)
    shop_info = cache.get(f"shop_{shop_slug}_info_cache")

    context = {
        "subcategories": root_categories,
        "category": category,
        "shop": shop,
        "shop_info": shop_info,
    }
    return render(request, "products/shop_subcategories.html", context)


def shop_category_products(request, shop_slug, slug):
    shop = get_object_or_404(Shop, slug=shop_slug)
    category = get_object_or_404(Category, slug=slug)

    filters_data = get_shop_category_filters(category, shop)
    products = get_shop_filtered_products(category, shop, request)

    paginator = Paginator(products, request.GET.get("prod_count", 24))
    page_obj = paginator.get_page(request.GET.get("page"))

    if not cache.get(f"shop_{shop_slug}_info_cache"):
        set_shop_info_cache(shop_slug)
    shop_info = cache.get(f"shop_{shop_slug}_info_cache")

    context = {
        "category": category,
        "shop": shop,
        "page_obj": page_obj,
        "sort_parameter": request.GET.get("sort_by", "-pub_date"),
        **filters_data,
        "shop_info": shop_info,
    }
    return render(request, "products/shop_category_list.html", context)


def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    # --- Работа с сессией: сохраняем в ключе 'recently_viewed' ---
    session_key = 'recently_viewed'
    recent = request.session.get(session_key, [])

    # Убираем дубликат, если товар уже есть в списке
    if product_id in recent:
        recent.remove(product_id)
    # Вставляем в начало
    recent.insert(0, product_id)
    # Оставляем только 10 последних
    recent = recent[:10]

    # Сохраняем обратно в сессию
    request.session[session_key] = recent
    # При мутировании списка желательно отметить, что сессия изменилась
    request.session.modified = True  # :contentReference[oaicite:0]{index=0}

    in_cart = str(product_id) in Cart(request).cart

    reviews_stats = product.reviews.aggregate(
        avg_rating=Avg('rating'),
        reviews_count=Count('id')
    )
    avg_rating = reviews_stats.get('avg_rating')
    reviews_count = reviews_stats.get('reviews_count')

    # Определяем, может ли пользователь оставить новый отзыв
    can_review = False
    if request.user.is_authenticated:
        order_items_count = OrderItem.objects.filter(order__user=request.user, product=product).count()
        user_reviews_count = product.reviews.filter(user=request.user).count()
        if order_items_count > user_reviews_count:
            can_review = True

    context = {
        "product": product,
        "in_cart": in_cart,
        "avg_rating": avg_rating,
        "reviews_count": reviews_count,
        "can_review": can_review,
    }
    return render(request, "products/product_detail.html", context)


@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # Подсчитываем, сколько раз пользователь заказывал данный товар
    order_items_count = OrderItem.objects.filter(
        order__user=request.user,
        product=product
    ).count()
    # Подсчитываем, сколько отзывов он уже оставил по данному товару
    reviews_count = Review.objects.filter(
        product=product,
        user=request.user
    ).count()
    if reviews_count >= order_items_count:
        messages.error(request, "Вы не можете оставить отзыв, "
                                "так как оставлено максимально допустимое количество отзывов для данного товара.")
        return redirect('product_detail', product_id=product_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.save()
            messages.success(request, "Отзыв успешно добавлен!")
            return redirect('product_reviews', product_id=product_id)
    else:
        form = ReviewForm()

    return render(request, 'products/add_review.html', {'form': form, 'product': product})


@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Отзыв успешно обновлен!")
            url = reverse('product_reviews', kwargs={'product_id': review.product.id})
            # Добавляем фрагмент "#review-<pk>" к URL
            return redirect(f"{url}#review-{review.pk}")
    else:
        form = ReviewForm(instance=review)
    return render(request, 'products/edit_review.html', {'form': form, 'product': review.product})


def product_reviews(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = Review.objects.filter(product=product).order_by('-pub_date')
    paginator = Paginator(reviews, 24)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'products/product_reviews.html', {
        'product': product,
        'page_obj': page_obj
    })
