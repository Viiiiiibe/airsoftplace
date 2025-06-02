from django.contrib import admin
from .models import Order, ShippingAddress, OrderItem, StoreSalesReport
from django.http import HttpResponse
from openpyxl import Workbook


class OrderAdmin(admin.ModelAdmin):
    list_display = ('pk', 'shop', 'customer_email', 'customer_last_name', 'customer_first_name', 'customer_patronymic',
                    'amount', 'created', 'updated', 'status')
    search_fields = ('pk', 'customer_email', 'customer_last_name', 'customer_first_name', 'customer_patronymic',)
    list_filter = ('status', 'shop')
    empty_value_display = '-пусто-'


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('pk', 'order', 'product', 'price', 'quantity')
    search_fields = ('pk',)
    list_filter = ('order', 'product')
    empty_value_display = '-пусто-'


class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'country', 'region', 'city', 'street', 'house', 'flat', 'floor', 'intercom')
    search_fields = ('pk', 'country', 'region', 'city', 'street', 'house', 'flat')
    list_filter = ('user', )
    empty_value_display = '-пусто-'


class StoreSalesReportAdmin(admin.ModelAdmin):
    list_display = ('pk', 'shop', 'start_date', 'end_date',)
    search_fields = ('pk',)
    list_filter = ('shop', 'start_date', 'end_date', )
    empty_value_display = '-пусто-'

    actions = ['download_excel']  # Добавляем новое действие

    @admin.action(description='Скачать Excel-отчет')
    def download_excel(self, request, queryset):
        # Создаем Excel-книгу
        wb = Workbook()
        ws = wb.active
        ws.title = "Отчеты о продажах"

        # Заголовки столбцов
        headers = [
            "ID отчета",
            "Магазин",
            "Начало периода",
            "Конец периода",
            "Выручка",
            "Комиссия площадки (14%)",
            "К выплате",
            "ИНН",
            "Расчётный счёт",
            "БИК",
        ]
        ws.append(headers)

        # Заполняем данные
        for report in queryset:

            row = [
                report.pk,
                str(report.shop),
                report.start_date.strftime("%Y-%m-%d"),
                report.end_date.strftime("%Y-%m-%d"),
                report.revenue,
                float(report.revenue) * 0.14,
                float(report.revenue) * 0.86,
                str(report.shop.INN),
                str(report.shop.payment_account),
                str(report.shop.BIC),
            ]
            ws.append(row)

        # Настраиваем HTTP-ответ
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=StoreSalesReports.xlsx'
        wb.save(response)

        return response


admin.site.register(Order, OrderAdmin)
admin.site.register(ShippingAddress, ShippingAddressAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(StoreSalesReport, StoreSalesReportAdmin)
