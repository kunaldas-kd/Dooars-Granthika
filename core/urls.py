# core/urls.py

from django.urls import path
from . import views

# app_name = "core"

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('pricing/', views.pricing, name='pricing'),
    path('contact/', views.contact, name='contact'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
]
