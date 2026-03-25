from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.admin_dashboard, name="admin_dashboard"),
    # path("collect-fine/<int:pk>/", views.collect_fine, name="collect_fine"),
]