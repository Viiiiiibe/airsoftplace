from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView
from django.contrib.auth.views import (
    LoginView, PasswordChangeView, PasswordResetView, PasswordResetConfirmView)
from django.urls import reverse_lazy
from products.models import Product
from .forms import RegisterForm, LoginForm, CustomUserChangeFromUserInterfaceForm, ShopRegistrationForm, \
    ProductUpdateForm, ProductForm
from cart.models import Order, StoreSalesReport
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import get_user_model
from .tasks import send_mail_to_support_task
from .tasks import send_order_status_email
from django.urls import reverse
from django.db.models import Q

User = get_user_model()


class SignUp(CreateView):
    form_class = RegisterForm
    success_url = reverse_lazy('index')
    template_name = 'users/signup.html'


class LoginView(LoginView):
    form_class = LoginForm
    template_name = 'users/login.html'


class UserPasswordChange(PasswordChangeView):
    success_url = reverse_lazy("users:password_change_done")
    template_name = "users/password_change_form.html"


class UserPasswordResetView(PasswordResetView):
    success_url = reverse_lazy("users:password_reset_done")
    template_name = "users/password_reset_form.html"


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    success_url = reverse_lazy("users:password_reset_complete")
    template_name = "users/password_reset_confirm.html"


@login_required
def personal_account_main(request):
    return render(request, 'users/personal_account_main.html')


@login_required
def personal_information_edit(request):
    if request.method == "POST":
        form = CustomUserChangeFromUserInterfaceForm(request.POST, instance=request.user)
        if form.is_valid():
            request.user = form.save(commit=False)
            request.user.save()
            return redirect('users:personal_account_main', )
    else:
        form = CustomUserChangeFromUserInterfaceForm(instance=request.user)
    return render(request, 'users/personal_account_main_personal_information.html', {'form': form})


@login_required
def personal_account_orders(request):
    orders_list = Order.objects.filter(user=request.user).order_by('-created')
    # Пагинация
    page = request.GET.get('page', 1)
    paginator = Paginator(orders_list, 24)
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)
    context = {
        'orders': orders,
    }
    return render(request, 'users/personal_account_orders.html', context)


@login_required
def personal_account_order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related(
            'shipping_address',
            'shop'
        ).prefetch_related('items__product'),
        pk=pk
    )
    if request.user != order.user:
        return redirect('users:orders', )
    owner = User.objects.filter(shop=order.shop).first()
    if request.method == 'POST':
        user_pk = request.user.pk
        message = request.POST.get("message", None)
        if message:
            # Отправка письма
            send_mail_to_support_task.delay(pk, order.shop.title, user_pk, message)
    context = {
        'order': order,
        'owner': owner,
    }
    return render(request, 'users/personal_account_order_detail.html', context)


@login_required
def shop_docs(request):
    user = request.user
    shop = user.shop  # Получаем напрямую связанный магазин

    if request.method == 'POST':
        form = ShopRegistrationForm(request.POST, request.FILES, instance=shop)
        if form.is_valid():
            new_shop = form.save(commit=False)
            new_shop.verified = False

            # Если магазин создается впервые
            if not shop:
                new_shop.save()
                user.shop = new_shop
                user.save()
            else:
                new_shop.save()

            return redirect('users:shop_docs')
    else:
        form = ShopRegistrationForm(instance=shop)

    context = {
        'form': form,
        'shop': shop
    }
    return render(request, 'users/shop_docs.html', context)


@login_required
def shop_orders(request):
    # Проверка наличия магазина у пользователя
    if not request.user.shop:
        return redirect('users:shop_docs')

    shop = request.user.shop
    keyword = request.GET.get("q")
    if keyword:
        orders_list = Order.objects.filter(
            shop=shop,
            paid=True,
            pk__icontains=keyword
        ).select_related(
            'shipping_address'
        ).prefetch_related(
            'items__product'
        ).order_by('-created')
    else:
        orders_list = Order.objects.filter(
            shop=shop,
            paid=True
        ).select_related(
            'shipping_address'
        ).prefetch_related(
            'items__product'
        ).order_by('-created')

    # Пагинация
    page = request.GET.get('page', 1)
    paginator = Paginator(orders_list, 24)
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    return render(request, 'users/shop_orders.html', {'orders': orders})


@login_required
def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=order_id, shop=request.user.shop)
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_OPTIONS):
            if new_status != 'awaiting_payment':
                order.status = new_status
                order.save()
                send_order_status_email.delay(order.pk)
        url = reverse('users:shop_orders', )
        page = request.POST.get("page", "")
        q = request.POST.get("q", "")
        return redirect(f"{url}?page={page}&q={q}#order-{order_id}")


@login_required
def shop_products(request):
    # Проверка прав доступа
    if not request.user.shop or not request.user.shop.verified:
        return redirect('users:shop_docs')

    shop = request.user.shop

    # Обработка формы добавления товара
    if request.method == 'POST' and 'add_product' in request.POST:
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.shop = shop
            product.save()
            form.save_m2m()  # Сохраняем ManyToMany поля
            return redirect('users:shop_products')
    else:
        form = ProductForm()

    # Получение списка товаров
    keyword = request.GET.get("q")
    if keyword:
        queryset = Q(name__icontains=keyword) | Q(category__title__icontains=keyword)
        # Если запрос состоит только из цифр, добавляем фильтр по pk
        if keyword.isdigit():
            queryset |= Q(pk__exact=keyword)
        products_list = Product.objects.filter(Q(shop=shop) & queryset).order_by('-pub_date')
    else:
        products_list = Product.objects.filter(shop=shop).order_by('-pub_date')

    # Пагинация
    page = request.GET.get('page', 1)
    paginator = Paginator(products_list, 24)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    # Формы для обновления количества
    update_forms = []
    for product in products:
        update_forms.append(ProductUpdateForm(instance=product))

    context = {
        'form': form,
        'products': products,
        'update_forms': zip(products, update_forms),
        'breadcrumbs_data': form.breadcrumbs_data if hasattr(form, 'breadcrumbs_data') else {}
    }
    return render(request, 'users/shop_products.html', context)


@login_required
def update_product_stock(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=product_id, shop=request.user.shop)
        form = ProductUpdateForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
        url = reverse('users:shop_products')
        page = request.POST.get("page", "")
        q = request.POST.get("q", "")
        return redirect(f"{url}?page={page}&q={q}#product-{product_id}")


@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id, shop=request.user.shop)

    # Получаем ВСЕ категории товара (не только листовые)
    product_categories = product.category.all()

    # Формируем breadcrumbs_data для категорий товара
    breadcrumbs_data = {}
    for cat in product_categories:
        breadcrumbs_data[str(cat.id)] = {
            'name': cat.title,
            'path': cat.get_ancestors(include_self=True)
        }
        # Добавляем всех предков для каждой категории
        for ancestor in cat.get_ancestors(include_self=True):
            breadcrumbs_data[str(ancestor.id)] = {
                'name': ancestor.title,
                'path': ancestor.get_ancestors(include_self=True)
            }

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            updated_product = form.save(commit=False)
            updated_product.verified = False
            updated_product.save()
            form.save_m2m()
            return redirect('users:shop_products')
    else:
        form = ProductForm(instance=product)

    context = {
        'form': form,
        'product': product,
        'breadcrumbs_data': breadcrumbs_data
    }
    return render(request, 'users/edit_product.html', context)


@login_required
def shop_statistics(request):
    if not request.user.shop:
        return redirect('users:shop_docs')

    shop = request.user.shop

    reports_list = StoreSalesReport.objects.filter(shop=shop).order_by('-end_date')

    paginator = Paginator(reports_list, 24)
    page = request.GET.get('page', 1)
    try:
        reports = paginator.page(page)
    except PageNotAnInteger:
        reports = paginator.page(1)
    except EmptyPage:
        reports = paginator.page(paginator.num_pages)

    context = {
        'reports': reports,
        'shop': shop
    }
    return render(request, 'users/shop_statistics.html', context)
