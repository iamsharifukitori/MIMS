from django.contrib import admin
from django.urls import path
from mims import views
from mims.views import dashboard_view, inventory_list_view
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('inventory/', inventory_list_view, name='inventory'),
    path('inventory/edit/<int:product_id>/', views.edit_product_view, name='edit_product'),
    path('sale/new/', views.create_sale_view, name='create_sale'),
    path('sales/ledger/', views.sale_ledger_view, name='sale_ledger'),
    path('sales/pay/<int:sale_id>/', views.pay_debt_view, name='pay_debt'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('expenses/', views.expense_list_view, name='expense_list'),
    path('login/', auth_views.LoginView.as_view(template_name='mims/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', auth_views.LoginView.as_view(template_name='mims/login.html'), name='login'),
    path('sale/<int:sale_id>/', views.view_sale_view, name='view_sale'),
    path('loans/', views.loans_list_view, name='loans_list'),
    path('barcode-lookup/', views.barcode_lookup, name='barcode_lookup'),
]