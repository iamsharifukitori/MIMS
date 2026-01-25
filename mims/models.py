from django.db import models
from django.utils import timezone
from django.db.models import Sum, F

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True) 
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    bulk_unit = models.CharField(max_length=50, help_text="e.g., Box, Carton")
    base_unit = models.CharField(max_length=50, help_text="e.g., Tablet, Piece, Bottle")
    conversion_factor = models.PositiveIntegerField(help_text="How many base units are in one bulk unit?")
    buy_price_per_bulk = models.DecimalField(max_digits=10, decimal_places=2)
    sell_price_per_base = models.DecimalField(max_digits=10, decimal_places=2)
    stock_qty = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

class Purchase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_bulk = models.PositiveIntegerField(help_text="Number of boxes/cartons bought")
    purchase_date = models.DateTimeField(default=timezone.now)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.pk: # Only add to stock on first creation
            added_stock = self.quantity_bulk * self.product.conversion_factor
            self.product.stock_qty += added_stock
            self.product.save()
        super().save(*args, **kwargs)

class Sale(models.Model):
    PAYMENT_CHOICES = [
        ('PAID', 'Paid'),
        ('LOAN', 'Loan/Credit'),
        ('PARTIAL', 'Partial Payment'),
    ]

    sale_date = models.DateTimeField(default=timezone.now)
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='PAID')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def balance_due(self):
        return self.total_amount - self.amount_paid

    def update_totals(self):
        """Calculates subtotal and final total from related SaleItems."""
        aggregate = self.items.aggregate(
            total=Sum(F('quantity_base') * F('price_at_sale'))
        )
        self.subtotal = aggregate['total'] or 0
        self.total_amount = self.subtotal - self.discount_amount
        # Using update to avoid re-triggering save logic if unnecessary
        Sale.objects.filter(pk=self.pk).update(
            subtotal=self.subtotal, 
            total_amount=self.total_amount
        )

    def __str__(self):
        return f"Sale {self.id} - {self.customer_name or 'Walk-in'}"

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_base = models.PositiveIntegerField(help_text="Units sold (tabs/pcs)")
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            self.product.stock_qty -= self.quantity_base
            self.product.save()
        
        super().save(*args, **kwargs)
        # Recalculate the parent sale totals
        self.sale.update_totals()

class Expense(models.Model):
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.description} - {self.amount}"

class Loan(Sale):
    class Meta:
        proxy = True
        verbose_name = "Customer Loan"
        verbose_name_plural = "Customer Loans & Debts"

class PaymentRecord(models.Model):
    sale = models.ForeignKey(Sale, related_name='payments', on_delete=models.CASCADE)
    date_paid = models.DateTimeField(default=timezone.now)
    amount_received = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=[
        ('CASH', 'Cash'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('CARD', 'Card/Bank Transfer')
    ], default='CASH')
    note = models.CharField(max_length=255, blank=True, help_text="Reference info (e.g. Transaction ID)")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Automatically update the parent Sale's amount_paid
        total_collected = PaymentRecord.objects.filter(sale=self.sale).aggregate(
            total=Sum('amount_received'))['total'] or 0
        
        self.sale.amount_paid = total_collected
        
        # Auto-update status based on balance
        if self.sale.amount_paid >= self.sale.total_amount:
            self.sale.payment_status = 'PAID'
        elif self.sale.amount_paid > 0:
            self.sale.payment_status = 'PARTIAL'
            
        self.sale.save()

    def __str__(self):
        return f"{self.sale.id} - ${self.amount_received} on {self.date_paid.date()}"