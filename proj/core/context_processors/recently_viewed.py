from products.models import Product
from django.db.models import Avg, Count


def recently_viewed(request):
    product_ids = request.session.get('recently_viewed', [])
    if not product_ids:
        return {}

    # Получаем объекты и сохраняем порядок из списка идентификаторов
    products = Product.objects.annotate(
                                    avg_rating=Avg('reviews__rating'),
                                    review_count=Count('reviews', distinct=True),
                                ).filter(id__in=product_ids)
    products_sorted = sorted(
        products,
        key=lambda prod: product_ids.index(prod.id)
    )
    return {'recently_viewed_products': products_sorted}
