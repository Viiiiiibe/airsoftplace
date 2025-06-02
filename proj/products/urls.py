from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('index/', views.index, name='index'),
    path('all_products/', views.all_products, name='all_products'),
    path('categories/', views.categories, name='categories'),
    path('categories/subcategories/<slug:slug>', views.subcategories, name='subcategories'),
    path('categories/<slug:slug>/', views.category_products, name='category_products'),

    path('shops/', views.shops, name='shops'),
    path('shops/<slug:shop_slug>/categories/', views.shop_categories, name='shop_categories'),
    path('shops/<slug:shop_slug>/categories/subcategories/<slug:slug>', views.shop_subcategories,
         name='shop_subcategories'),
    path('shops/<slug:shop_slug>/categories/<slug:slug>/', views.shop_category_products, name='shop_category_products'),

    path('product_detail/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product_detail/<int:product_id>/reviews/', views.product_reviews, name='product_reviews'),
    path('product_detail/<int:product_id>/add_review/', views.add_review, name='add_review'),
    path('review/<int:review_id>/edit/', views.edit_review, name='edit_review'),
]
