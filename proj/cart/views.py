from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from products.models import Product, Shop
from .cart import Cart
from .forms import MakingAnOrderForm
from proj.settings import AUTH_USER_MODEL
from yookassa import Configuration, Payment
from proj.settings import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
import uuid
from django.urls import reverse
from .models import ShippingAddress, Order, OrderItem
from decimal import Decimal
from .services import get_cdek_shipping_cost

User = AUTH_USER_MODEL

Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY


def cart_view(request):
    cart = Cart(request)
    grouped_items = {}

    # Группируем товары по shop_slug
    for item in cart:
        shop_slug = item['shop_slug']

        if shop_slug not in grouped_items:
            try:
                shop = Shop.objects.get(slug=shop_slug)
            except Shop.DoesNotExist:
                continue
            grouped_items[shop_slug] = {
                'shop': shop,
                'items': [],
                'total': Decimal('0.00'),
            }

        grouped_items[shop_slug]['items'].append(item)
        grouped_items[shop_slug]['total'] += Decimal(item['price']) * item['qty']

    context = {
        'grouped_items': grouped_items.values(),
    }
    return render(request, 'cart/cart-view.html', context)


def cart_add(request):
    cart = Cart(request)

    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))
        product_qty = int(request.POST.get('product_qty'))

        product = get_object_or_404(Product, pk=product_id)

        cart.add(product=product, quantity=product_qty)

        cart_qty = cart.__len__()

        response = JsonResponse({'qty': cart_qty, "product": product.name})

        return response


def cart_delete(request):
    cart = Cart(request)

    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))

        cart.delete(product=product_id)

        cart_qty = cart.__len__()

        cart_total = cart.get_total_price()

        response = JsonResponse({'qty': cart_qty, 'total': cart_total})

        return response


def cart_update(request):
    cart = Cart(request)

    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))

        if Product.objects.get(pk=product_id).items_left is None:
            prod_items_left = 10000
        else:
            prod_items_left = Product.objects.get(pk=product_id).items_left

        if (int(request.POST.get('product_qty')) < prod_items_left) and (int(request.POST.get('product_qty')) > 1):
            product_qty = int(request.POST.get('product_qty'))
        elif int(request.POST.get('product_qty')) <= 1:
            product_qty = 1
        else:
            product_qty = prod_items_left

        cart.update(product=product_id, quantity=product_qty)

        cart_qty = cart.__len__()
        cart_total = cart.get_total_price()

        response = JsonResponse({'qty': cart_qty, 'total': cart_total})

        return response


def order_view(request, shop_slug):
    cart = Cart(request)
    try:
        shop = Shop.objects.get(slug=shop_slug)
    except Shop.DoesNotExist:
        return redirect('cart:cart-view')

    # Фильтрация товаров корзины по shop_slug
    shop_items = []
    total_price = Decimal('0.00')
    for product_id, item_data in cart.cart.items():
        if item_data.get('shop_slug') == shop_slug:
            product = Product.objects.get(pk=product_id)
            quantity = item_data['qty']
            price = Decimal(item_data['price'])
            total_price += price * quantity
            shop_items.append({
                'product': product,
                'qty': quantity,
                'price': price,
            })

    if not shop_items:
        return redirect('cart:cart-view')

    if request.method == 'POST' and 'find_shipping_cost_to_city' in request.POST:
        delivery_city = request.POST.get('find_shipping_cost_to_city', '').strip().lower()
        delivery_method = request.POST.get("find_shipping_cost_with_method", '')
        if not delivery_city or not delivery_method:
            return JsonResponse({'error': 'Укажите город и способ доставки'}, status=400)

        total_shipping = Decimal('0.00')

        # Группируем товары по городам склада
        warehouses = {}
        for item in shop_items:
            product = item['product']
            warehouse = product.warehouse_city
            if warehouse not in warehouses:
                warehouses[warehouse] = []
            warehouses[warehouse].append(product)

        for warehouse, products in warehouses.items():
            # Рассчитываем объемный вес для группы
            volumetric_weight = Decimal('0.00')
            for product in products:
                try:
                    volumetric = (Decimal(product.shipping_width) * Decimal(product.shipping_length) * Decimal(
                        product.shipping_height)) / Decimal('5000')
                    volumetric_weight += max(volumetric, Decimal(product.shipping_weight))
                except Exception:
                    continue

            # Получаем стоимость доставки
            try:
                cost = get_cdek_shipping_cost(warehouse.strip().lower(), delivery_city, volumetric_weight,
                                              delivery_method)
                total_shipping += cost
            except Exception:
                return JsonResponse({'error': 'Укажите город и способ доставки'}, status=400)

        return JsonResponse({
            'shipping_cost': f"{total_shipping:.2f}"
        })

    if request.method == 'POST' and 'find_shipping_cost_to_city' not in request.POST:
        delivery_method = request.POST.get("shipping", '')
        delivery_country = "Россия"
        if delivery_method == 'Пункт выдачи':
            delivery_region = request.POST.get("pickup-point-region", )
            delivery_city = request.POST.get("pickup-point-city", )
            delivery_street = request.POST.get("pickup-point-street", )
            delivery_house = request.POST.get("pickup-point-house", )
            delivery_flat = ''
            delivery_entrance = ''
            delivery_floor = ''
            delivery_intercom = ''
        elif delivery_method == 'Курьером':
            delivery_region = request.POST.get("courier-delivery-region", )
            delivery_city = request.POST.get("courier-delivery-city", )
            delivery_street = request.POST.get("courier-delivery-street", )
            delivery_house = request.POST.get("courier-delivery-house", )
            delivery_flat = request.POST.get("courier-delivery-flat", )
            delivery_entrance = request.POST.get("courier-delivery-entrance", )
            delivery_floor = request.POST.get("courier-delivery-floor", )
            delivery_intercom = request.POST.get("courier-delivery-intercom", )
        form = MakingAnOrderForm(request.POST)
        if not form.is_valid():
            # Вернём форму с ошибками, чтобы пользователь их поправил
            return render(request, 'cart/order.html', {
                            'items': shop_items,
                            'total_price': total_price,
                            'form': form,
                            'shop': shop,
            })
        cd = form.cleaned_data
        customer_last_name = cd['customer_last_name']
        customer_first_name = cd['customer_first_name']
        customer_patronymic = cd.get('customer_patronymic', '')
        customer_email = cd['customer_email']
        customer_phone = cd['customer_phone']

        if request.user.is_authenticated:
            shipping_address, _ = ShippingAddress.objects.get_or_create(
                user=request.user,
                country=delivery_country,
                region=delivery_region,
                city=delivery_city,
                street=delivery_street,
                house=delivery_house,
                flat=delivery_flat,
                entrance=delivery_entrance,
                floor=delivery_floor,
                intercom=delivery_intercom,
                defaults={
                    'user': request.user,
                    'country': delivery_country,
                    'region': delivery_region,
                    'city': delivery_city,
                    'street': delivery_street,
                    'house': delivery_house,
                    'flat': delivery_flat,
                    'entrance': delivery_entrance,
                    'floor': delivery_floor,
                    'intercom': delivery_intercom,
                }
            )

            order = Order.objects.create(
                user=request.user,
                shop=shop,
                shipping_address=shipping_address,
                customer_last_name=customer_last_name,
                customer_first_name=customer_first_name,
                customer_patronymic=customer_patronymic,
                customer_email=customer_email,
                customer_phone=customer_phone,
                delivery_method=delivery_method,
                amount=total_price,
            )

            idempotence_key = uuid.uuid4()

            currency = 'RUB'
            description = f'Оплата заказа {order.pk} из магазина {shop.title} на платформе AirsoftPlace'
            try:
                payment = Payment.create({
                    "amount": {
                        "value": str(total_price),
                        "currency": currency
                    },
                    "confirmation": {
                        "type": "redirect",
                        "return_url": request.build_absolute_uri(reverse('cart:payment-success')),
                    },
                    "capture": True,
                    "test": True,
                    "description": description,
                    "metadata": {  # добавляем метаданные с ID заказа
                        "order_id": order.pk if order else None
                    },
                }, idempotence_key)
                # Обновляем заказ с payment_id
                order.payment_id = payment.id
                order.save()

                confirmation_url = payment.confirmation.confirmation_url

                for item in shop_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item['product'],
                        price=item['price'],
                        quantity=item['qty'],
                    )
                    # Удаляем товары из корзины
                    item_product = item.get('product')
                    cart.delete(product=int(item_product.pk))

                return redirect(confirmation_url)
            except Exception:
                # Удаляем заказ, если платеж не создан
                order.delete()
                return redirect('cart:payment-error', )

        else:
            shipping_address, _ = ShippingAddress.objects.get_or_create(
                country=delivery_country,
                region=delivery_region,
                city=delivery_city,
                street=delivery_street,
                house=delivery_house,
                flat=delivery_flat,
                entrance=delivery_entrance,
                floor=delivery_floor,
                intercom=delivery_intercom,
                defaults={
                    'country': delivery_country,
                    'region': delivery_region,
                    'city': delivery_city,
                    'street': delivery_street,
                    'house': delivery_house,
                    'flat': delivery_flat,
                    'entrance': delivery_entrance,
                    'floor': delivery_floor,
                    'intercom': delivery_intercom,
                }
            )

            order = Order.objects.create(
                shop=shop,
                shipping_address=shipping_address,
                customer_last_name=customer_last_name,
                customer_first_name=customer_first_name,
                customer_patronymic=customer_patronymic,
                customer_email=customer_email,
                customer_phone=customer_phone,
                delivery_method=delivery_method,
                amount=total_price,
            )

            idempotence_key = uuid.uuid4()

            currency = 'RUB'
            description = f'Оплата заказа {order.pk} из магазина {shop.title} на платформе AirsoftPlace'
            try:
                payment = Payment.create({
                    "amount": {
                        "value": str(total_price),
                        "currency": currency
                    },
                    "confirmation": {
                        "type": "redirect",
                        "return_url": request.build_absolute_uri(reverse('cart:payment-success')),
                    },
                    "capture": True,
                    "test": True,
                    "description": description,
                    "metadata": {  # добавляем метаданные с ID заказа
                        "order_id": order.pk if order else None
                    },
                }, idempotence_key)
                # Обновляем заказ с payment_id
                order.payment_id = payment.id
                order.save()

                confirmation_url = payment.confirmation.confirmation_url

                for item in shop_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item['product'],
                        price=item['price'],
                        quantity=item['qty'],
                    )
                    # Удаляем товары из корзины
                    item_product = item.get('product')
                    cart.delete(product=int(item_product.pk))

                return redirect(confirmation_url)
            except Exception:
                # Удаляем заказ, если платеж не создан
                order.delete()
                return redirect('cart:payment-error', )
    else:
        if request.user.is_authenticated:
            form = MakingAnOrderForm(
                initial={
                    'customer_last_name': request.user.last_name,
                    'customer_first_name': request.user.first_name,
                    'customer_patronymic': request.user.patronymic,
                    'customer_email': request.user.email,
                    'customer_phone': request.user.phone_number,
                }
            )
        else:
            form = MakingAnOrderForm()

    context = {
        'items': shop_items,
        'total_price': total_price,
        'form': form,
        'shop': shop,
    }

    return render(request, 'cart/order.html', context)


def payment_success(request):
    return render(request, 'cart/payment_success.html')


def payment_error(request):
    return render(request, 'cart/payment_error.html')
