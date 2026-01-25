from django.contrib import admin
from django.urls import path
from mims import views
from mims.views import dashboard_view, inventory_list_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('inventory/', inventory_list_view, name='inventory'),
    path('sale/new/', views.create_sale_view, name='create_sale'),
]