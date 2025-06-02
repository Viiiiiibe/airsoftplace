from products.models import Shop
from proj.celery import app
from .models import Order, OrderItem, StoreSalesReport
from proj.settings import EMAIL_HOST_USER
from django.core.mail import send_mail
from django.template.loader import get_template
import logging
from django.db import transaction
from django.utils import timezone
import calendar
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger('django')


@app.task
def update_order_status(order_id):
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id)
            order.paid = True
            order.status = 'in_assembly'
            order.save(update_fields=['paid', 'status', 'updated'])
            logger.info(f"Order {order_id} status updated successfully")
    except Exception as e:
        logger.error(f"Error updating order status {order_id}: {str(e)}")


@app.task
def decrease_product_quantity(order_id):
    try:
        with transaction.atomic():
            order = Order.objects.get(pk=order_id)
            order_items = OrderItem.objects.filter(order=order).select_related('product')
            for item in order_items:
                product = item.product
                if product.items_left is not None:
                    product.items_left -= item.quantity
                    product.save()
            logger.info(f"Products decreased for order {order_id}")
    except Exception as e:
        logger.error(f"Error decreasing products for order {order_id}: {str(e)}")


@app.task
def update_store_sales_report(order_id):
    try:
        with transaction.atomic():
            # Блокируем связанные объекты для избежания race condition
            order = Order.objects.select_related('shop').select_for_update().get(pk=order_id)
            shop = order.shop

            # Находим подходящий отчет
            today = timezone.now().date()
            report = StoreSalesReport.objects.filter(
                shop=shop,
                start_date__lte=today,
                end_date__gte=today
            ).select_for_update().first()

            # Если нет активного отчета, создаем
            if not report:
                first_day_this_month = today.replace(day=1)
                _, last_day = calendar.monthrange(today.year, today.month)
                last_day_this_month = today.replace(day=last_day)

                report = StoreSalesReport.objects.create(
                    shop=shop,
                    start_date=first_day_this_month,
                    end_date=last_day_this_month,
                    revenue=Decimal('0.00'),
                    products_performance={},
                    category_performance={}
                )

            # Обновляем выручку
            report.revenue += order.amount
            report.save(update_fields=['revenue'])

            # Добавляем заказ в отчет
            report.orders.add(order)

            # Обновляем продажи по товарам
            products_perf = report.products_performance.copy()
            for item in order.items.select_related('product').all():
                product_id = str(item.product.pk)
                products_perf[product_id] = products_perf.get(product_id, 0) + item.quantity
            report.products_performance = products_perf

            # Обновляем продажи по категориям
            category_perf = report.category_performance.copy()
            for item in order.items.select_related('product').all():
                for category in item.product.category.all():
                    category_slug = category.slug
                    category_perf[category_slug] = category_perf.get(category_slug, 0) + item.quantity
            report.category_performance = category_perf

            report.save()
            logger.info(f"Updated sales report {report.id} for order {order_id}")

    except Exception as e:
        logger.error(f"Error updating sales report for order {order_id}: {str(e)}")


@app.task
def send_email_to_owner(order_id):
    try:
        order = Order.objects.select_related(
            'shop',
            'shipping_address'
        ).prefetch_related(
            'items__product'
        ).get(pk=order_id)

        # Получаем владельца магазина
        owner = User.objects.filter(shop=order.shop).first()
        if not owner or not owner.email:
            logger.warning(f"No owner email for shop {order.shop.id}")
            return

        context = {'order': order}

        send_mail(
            subject=f'Новый заказ №{order.id}',
            message='',
            from_email=EMAIL_HOST_USER,
            recipient_list=[owner.email],
            fail_silently=False,
            html_message=get_template('email/order_notification_owner.html').render(context)
        )

        logger.info(f"Email sent to shop owner for order {order_id}")

    except Exception as e:
        logger.error(f"Error sending email to owner: {str(e)}")


@app.task
def send_email_to_customer(order_id):
    try:
        order = Order.objects.select_related(
            'shipping_address'
        ).prefetch_related(
            'items__product'
        ).get(pk=order_id)

        if not order.customer_email:
            logger.warning(f"No customer email in order {order_id}")
            return

        context = {'order': order}

        send_mail(
            subject=f'Ваш заказ №{order.id} принят',
            message='',
            from_email=EMAIL_HOST_USER,
            recipient_list=[order.customer_email],
            fail_silently=False,
            html_message=get_template('email/order_notification_customer.html').render(context)
        )

        logger.info(f"Email sent to customer for order {order_id}")

    except Exception as e:
        logger.error(f"Error sending email to customer: {str(e)}")


@app.task
def create_monthly_reports():
    try:
        with transaction.atomic():
            # Текущая дата
            today = timezone.now().date()

            # Вычисляем первый день следующего месяца
            if today.month == 12:
                next_month = 1
                next_year = today.year + 1
            else:
                next_month = today.month + 1
                next_year = today.year

            first_day_next_month = date(next_year, next_month, 1)

            # Последний день следующего месяца
            _, last_day_next_month = calendar.monthrange(next_year, next_month)
            last_day_next_month = date(next_year, next_month, last_day_next_month)

            # Находим магазины без отчета на следующий месяц
            existing_shops = StoreSalesReport.objects.filter(
                start_date=first_day_next_month,
                end_date=last_day_next_month
            ).values_list('shop_id', flat=True)

            shops = Shop.objects.exclude(id__in=existing_shops)

            # Создаем отчеты
            reports = [
                StoreSalesReport(
                    shop=shop,
                    start_date=first_day_next_month,
                    end_date=last_day_next_month,
                    revenue=Decimal('0.00'),
                    products_performance={},
                    category_performance={}
                ) for shop in shops
            ]

            if reports:
                StoreSalesReport.objects.bulk_create(reports)
                logger.info(f"Created {len(reports)} reports for {first_day_next_month.strftime('%Y-%m')}")
            else:
                logger.info("No new reports needed")

    except Exception as e:
        logger.error(f"Error creating reports: {str(e)}", exc_info=True)


@app.task
def delete_order_with_canceled_payment(order_id):
    try:
        with transaction.atomic():
            Order.objects.select_for_update().get(pk=order_id).delete()
    except Exception as e:
        logger.error(f"Error deleting order with canceled payment {order_id}: {str(e)}")
