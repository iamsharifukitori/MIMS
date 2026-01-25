from django.contrib import admin, messages
from django.db import models
from django.utils.html import format_html
from django.urls import reverse
from .models import Category, PaymentRecord, Product, Purchase, Sale, SaleItem, Expense, Loan

# --- INLINES (Must be defined first) ---

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1  # Provides one empty row by default for new items

class PaymentRecordInline(admin.TabularInline):
    model = PaymentRecord
    extra = 1  # Allows you to add a new payment line easily
    fields = ('date_paid', 'amount_received', 'payment_method', 'note')

# --- ADMIN CLASSES ---

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'stock_qty', 'base_unit', 'sell_price_per_base')
    list_filter = ('category',)
    search_fields = ('name',)
    readonly_fields = ('stock_qty',)
    
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'category')}),
        ('Unit Conversion', {
            'fields': ('bulk_unit', 'base_unit', 'conversion_factor'),
            'description': "Define how many small units are in one bulk box."
        }),
        ('Pricing & Stock', {'fields': ('buy_price_per_bulk', 'sell_price_per_base', 'stock_qty')}),
    )

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity_bulk', 'purchase_date', 'total_cost')
    list_filter = ('purchase_date', 'product')
    date_hierarchy = 'purchase_date'

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'payment_status', 'total_amount', 'amount_paid', 'due_balance', 'sale_date')
    list_filter = ('payment_status', 'sale_date')
    search_fields = ('customer_name',)
    inlines = [SaleItemInline, PaymentRecordInline]
    readonly_fields = ('amount_paid', 'subtotal', 'total_amount')
    
    def due_balance(self, obj):
        balance = obj.total_amount - obj.amount_paid
        return balance
    due_balance.short_description = "Balance Due"

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'date')
    list_filter = ('date',)

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    # Integrated display including editable payments and invoice links
    list_display = ('customer_name', 'total_amount', 'amount_paid', 'balance_due_display', 'payment_status', 'sale_link', 'sale_date')
    list_editable = ('amount_paid', 'payment_status')
    list_filter = ('sale_date',)
    search_fields = ('customer_name',)
    inlines = [PaymentRecordInline]
    fields = ('customer_name', 'total_amount', 'amount_paid', 'payment_status')
    readonly_fields = ('customer_name', 'total_amount')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(total_amount__gt=models.F('amount_paid'))

    def balance_due_display(self, obj):
        amount = obj.balance_due()
        return format_html('<span style="color: red; font-weight: bold;">${}</span>', amount)
    balance_due_display.short_description = "Outstanding Debt"

    def sale_link(self, obj):
        # IMPORTANT: Change 'yourappname' to your actual Django app name
        url = reverse("admin:yourappname_sale_change", args=[obj.id])
        return format_html('<a class="button" href="{}">View Full Invoice</a>', url)
    sale_link.short_description = "Actions"

    def save_model(self, request, obj, form, change):
        if obj.amount_paid >= obj.total_amount:
            obj.payment_status = 'PAID'
        elif obj.amount_paid > 0:
            obj.payment_status = 'PARTIAL'
        super().save(request, obj, form, change)