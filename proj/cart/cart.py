from decimal import Decimal

from products.models import Product


class Cart():

    def __init__(self, request) -> None:

        self.session = request.session

        cart = self.session.get('session_key')

        if not cart:
            cart = self.session['session_key'] = {}

        self.cart = cart

    def __len__(self):
        return sum(item['qty'] for item in self.cart.values())

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(pk__in=product_ids)
        cart = self.cart.copy()

        for product in products:
            cart[str(product.pk)]['product'] = product

        for item in cart.values():
            item['price'] = Decimal(item['price'])
            item['total'] = item['price'] * item['qty']
            yield item

    def add(self, product, quantity):

        product_id = str(product.pk)
        shop_slug = product.shop.slug

        if product_id not in self.cart:
            self.cart[product_id] = {'qty': quantity, 'price': str(product.price), 'shop_slug': shop_slug, }
            self.cart[product_id]['qty'] = quantity

        self.session.modified = True

    def delete(self, product):
        product_id = str(product)
        if product_id in self.cart:
            del self.cart[product_id]
            self.session.modified = True

    def update(self, product, quantity):
        product_id = str(product)
        if product_id in self.cart:
            self.cart[product_id]['qty'] = quantity
            self.session.modified = True

    def get_total_price(self):
        return sum(Decimal(item['price']) * item['qty'] for item in self.cart.values())
