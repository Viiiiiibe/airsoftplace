from django.contrib import admin
from mptt.fields import TreeManyToManyField
from .models import Product, Category, Shop, Review
from mptt.admin import DraggableMPTTAdmin
from django.forms import CheckboxSelectMultiple


class ProductAdmin(admin.ModelAdmin):
    list_display = ('pk', 'shop', 'categories', 'name', 'verified')
    search_fields = ('pk', 'name', )
    list_filter = ('category', 'verified', 'shop',)
    empty_value_display = '-пусто-'
    list_editable = ('verified',)
    formfield_overrides = {
        TreeManyToManyField: {'widget': CheckboxSelectMultiple},
    }


class CategoryAdmin(DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title', 'slug',)
    mptt_level_indent = 20

    def get_prepopulated_fields(self, request, obj=None):
        return {
            'slug': ('title',),
        }


class ReviewAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'product', 'pub_date', 'show')
    search_fields = ('pk', )
    list_filter = ('user', 'product', 'show',)
    empty_value_display = '-пусто-'
    list_editable = ('show',)


class ShopAdmin(admin.ModelAdmin):
    list_display = ('pk', 'title', 'slug', 'type', 'verified')
    search_fields = ('pk', 'title', 'slug',)
    list_filter = ('type', 'verified')
    empty_value_display = '-пусто-'
    list_editable = ('verified',)


admin.site.register(Product, ProductAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Shop, ShopAdmin)
admin.site.register(Review, ReviewAdmin)
