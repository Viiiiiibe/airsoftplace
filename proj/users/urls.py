from django.contrib.auth.views import (
    LogoutView, PasswordChangeDoneView,
    PasswordResetDoneView, PasswordResetCompleteView
)
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('signup/', views.SignUp.as_view(), name='signup'),
    path(
        'logout/',
        LogoutView.as_view(template_name='users/logged_out.html'),
        name='logout'
    ),
    path('login/', views.LoginView.as_view(), name='login'),
    path(
        'password_change/',
        views.UserPasswordChange.as_view(template_name='users/password_change_form.html'),
        name='password_change'
    ),
    path(
        'password-change/done/',
        PasswordChangeDoneView.as_view(template_name='users/password_change_done.html'),
        name='password_change_done'
    ),

    path(
        'password_reset/',
        views.UserPasswordResetView.as_view(template_name='users/password_reset_form.html'),
        name='password_reset'
    ),
    path(
        'password_reset/done/',
        PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'),
        name='password_reset_done'
    ),

    path(
        'reset/<uidb64>/<token>/',
        views.UserPasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'),
        name='password_reset_confirm'
    ),
    path(
        'reset/done/',
        PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
        name='password_reset_complete'
    ),

    path('account/', views.personal_account_main, name='personal_account_main'),
    path('account/personal_information/', views.personal_information_edit, name='personal_information'),
    path('account/orders/', views.personal_account_orders, name='orders'),
    path('account/orders/<int:pk>/', views.personal_account_order_detail, name='order_detail'),

    path('shop_docs/', views.shop_docs, name='shop_docs'),
    path('shop_orders/', views.shop_orders, name='shop_orders'),
    path('shop_orders/update/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('shop_products/', views.shop_products, name='shop_products'),
    path('shop_products/update/<int:product_id>/', views.update_product_stock, name='update_product_stock'),
    path('shop_products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('shop_statistics/', views.shop_statistics, name='shop_statistics'),

]
