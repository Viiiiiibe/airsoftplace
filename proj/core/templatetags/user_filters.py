from django import template

from products.models import Category, Product

register = template.Library()


@register.filter
def addclass(field, css):
    return field.as_widget(attrs={'class': css})


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, {})


@register.filter
def get_category_by_id(cat_id):
    try:
        return Category.objects.get(id=int(cat_id))
    except (Category.DoesNotExist, ValueError):
        return None


@register.filter
def get_product_by_id(product_id):
    try:
        return Product.objects.get(id=int(product_id))
    except (Product.DoesNotExist, ValueError):
        return None


@register.filter
def getlist(querydict, key):
    """
    Возвращает список значений из request.GET.getlist(key).
    Usage: {{ request.GET|getlist:"foo" }}
    """
    return querydict.getlist(key)
