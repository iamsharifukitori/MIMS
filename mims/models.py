from django.db import models
from django.utils import timezone
from django.db.models import Sum, F
from decimal import Decimal, InvalidOperation

class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True) 
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    bulk_unit = models.CharField(max_length=50, help_text="e.g., Box")
    base_unit = models.CharField(max_length=50, help_text="e.g., Piece")
    conversion_factor = models.PositiveIntegerField(help_text="Sellable Items per Box")
    expiry_date = models.DateField(null=True, blank=True, help_text="Date when product expires")
    barcode = models.CharField(max_length=50, blank=True, null=True, unique=True)
    
    # NOTE: Stores the BUY PRICE OF THE SMALLEST UNIT
    buy_price_per_bulk = models.DecimalField(max_digits=10, decimal_places=2, help_text="Buy Price per Smallest Unit")
    sell_price_per_base = models.DecimalField(max_digits=10, decimal_places=2, help_text="Retail Price per Smallest Unit")
    
    # Stores the Number of BULK UNITS (Boxes)
    stock_qty = models.FloatField(default=0, help_text="Current Stock in Boxes") 

    @property
    def stock_value(self):
        try:
            boxes = Decimal(str(self.stock_qty))
            items_per_box = Decimal(str(self.conversion_factor))
            unit_buy_price = Decimal(str(self.buy_price_per_bulk))
            return boxes * items_per_box * unit_buy_price
        except (ValueError, TypeError, InvalidOperation):
            return Decimal(0)

    def __str__(self):
        return self.name

class Purchase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_bulk = models.PositiveIntegerField()
    purchase_date = models.DateTimeField(default=timezone.now)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.pk: 
            self.product.stock_qty += self.quantity_bulk
            self.product.save()
        super().save(*args, **kwargs)

class Sale(models.Model):
    PAYMENT_CHOICES = [('PAID', 'Paid'), ('LOAN', 'Loan'), ('PARTIAL', 'Partial')]
    sale_date = models.DateTimeField(default=timezone.now)
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='PAID')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

    def update_status(self):
        if self.amount_paid >= self.total_amount:
            self.payment_status = 'PAID'
        elif self.amount_paid > 0:
            self.payment_status = 'PARTIAL'
        else:
            self.payment_status = 'LOAN'
        self.save()
        
    def update_totals(self):
        aggregate = self.items.aggregate(
            total=Sum(F('quantity_base') * F('price_at_sale'))
        )
        self.subtotal = aggregate['total'] or 0
        self.total_amount = self.subtotal - self.discount_amount
        Sale.objects.filter(pk=self.pk).update(
            subtotal=self.subtotal, 
            total_amount=self.total_amount
        )

    def __str__(self):
        return f"Sale {self.id} - {self.customer_name}"

class PaymentRecord(models.Model):
    sale = models.ForeignKey(Sale, related_name='payments', on_delete=models.CASCADE)
    date_paid = models.DateTimeField(default=timezone.now)
    amount_received = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, default='CASH')
    note = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        total = PaymentRecord.objects.filter(sale=self.sale).aggregate(Sum('amount_received'))['amount_received__sum'] or 0
        self.sale.amount_paid = total
        self.sale.update_status()

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_base = models.PositiveIntegerField(help_text="Small units sold")
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.pk:
            try:
                qty_sold = Decimal(str(self.quantity_base))
                conv_rate = Decimal(str(self.product.conversion_factor))
                reduction = qty_sold / conv_rate
                current_stock = Decimal(str(self.product.stock_qty))
                self.product.stock_qty = float(current_stock - reduction)
                self.product.save()
            except (ZeroDivisionError, InvalidOperation, TypeError):
                pass 
        super().save(*args, **kwargs)
        self.sale.update_totals()
        
class Loan(Sale):
    class Meta:
        proxy = True
        verbose_name = "Customer Loan"
        verbose_name_plural = "Customer Loans"

class Expense(models.Model):
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)