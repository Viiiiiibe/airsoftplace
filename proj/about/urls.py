from django.urls import path
from . import views

app_name = 'about'

urlpatterns = [
    path('our_team/', views.our_team, name='our_team'),
    path('contacts/', views.contacts, name='contacts'),
    path('faq/', views.faq, name='faq'),
]
