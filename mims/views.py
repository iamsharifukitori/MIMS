from django.shortcuts import render, redirect
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta
from .models import Sale, SaleItem, Product, Expense, Purchase
from .forms import SaleForm

def dashboard_stats(request):
    # 1. Most Moving Product (By Quantity Sold)
    most_moving = SaleItem.objects.values('product__name').annotate(
        total_sold=Sum('quantity_base')
    ).order_by('-total_sold').first()

    # 2. Most Profitable Product (By Profit Margin * Quantity)
    most_profitable = Product.objects.annotate(
        total_profit=Sum(
            (F('sell_price_per_base') - (F('buy_price_per_bulk') / F('conversion_factor'))) * F('saleitem__quantity_base')
        )
    ).order_by('-total_profit').first()

    # 3. Monthly Sales Chart Data
    sales_data = Sale.objects.extra(select={'day': 'date(sale_date)'}).values('day').annotate(total=Sum('total_amount'))

    context = {
        'most_moving': most_moving,
        'most_profitable': most_profitable,
        'sales_data': sales_data,
    }
    return render(request, 'dashboard.html', context)

def dashboard_view(request):
    # --- Integration: Time-based Revenue Stats ---
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # Optimization: Aggregate daily and monthly in fewer hits
    daily_revenue = Sale.objects.filter(sale_date__date=today).aggregate(total=Sum('total_amount'))['total'] or 0
    monthly_revenue = Sale.objects.filter(sale_date__date__gte=start_of_month).aggregate(total=Sum('total_amount'))['total'] or 0

    # --- Your Original Logic (Preserved) ---
    most_moving = SaleItem.objects.values('product__name').annotate(
        total_sold=Sum('quantity_base')
    ).order_by('-total_sold').first()

    most_profitable = Product.objects.annotate(
        profit_per_unit=F('sell_price_per_base') - (F('buy_price_per_bulk') / F('conversion_factor'))
    ).order_by('-profit_per_unit').first()

    # --- Integration: Graph Data (Last 7 Days) ---
    graph_labels = []
    graph_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        rev = Sale.objects.filter(sale_date__date=day).aggregate(total=Sum('total_amount'))['total'] or 0
        graph_labels.append(day.strftime('%a')) 
        graph_data.append(float(rev))

    context = {
        'most_moving': most_moving,
        'most_profitable': most_profitable,
        'daily_revenue': daily_revenue,
        'monthly_revenue': monthly_revenue,
        'graph_labels': graph_labels,
        'graph_data': graph_data,
        'active_loans': Sale.objects.filter(total_amount__gt=F('amount_paid')).count()
    }
    return render(request, 'mims/dashboard.html', context)

def inventory_list_view(request):
    # OPTIMIZATION: select_related('category') joins tables in 1 query instead of N queries
    # Removed the redeclaration bug from inside the loop
    products = Product.objects.select_related('category').all().order_by('name')
    
    inventory_data = []
    for product in products:
        # (Stock Quantity / Conversion Factor) * Buy Price
        # Fixed: Ensuring conversion_factor isn't zero to avoid crash
        factor = product.conversion_factor if product.conversion_factor > 0 else 1
        stock_value = (product.stock_qty / factor) * float(product.buy_price_per_bulk)
        
        inventory_data.append({
            'item': product,
            'stock_value': stock_value,
            'is_low_stock': product.stock_qty < 20
        })

    return render(request, 'mims/inventory.html', {'inventory': inventory_data})

def create_sale_view(request):
    # OPTIMIZATION: Only fetch needed fields for the dropdown
    products = Product.objects.all()
    if request.method == 'POST':
        # Processing multi-item lists from your Money-First form
        product_names = request.POST.getlist('product_name[]')
        quantities = request.POST.getlist('quantity[]')
        money_paid_list = request.POST.getlist('money_paid[]')

        if product_names:
            # Create Sale Header
            sale = Sale.objects.create(
                customer_name="Walk-in", 
                payment_status='PAID',
                sale_date=timezone.now()
            )
            
            total_paid = 0
            for name, qty, money in zip(product_names, quantities, money_paid_list):
                try:
                    product = Product.objects.get(name=name)
                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity_base=int(qty),
                        price_at_sale=product.sell_price_per_base
                    )
                    total_paid += float(money)
                except (Product.DoesNotExist, ValueError):
                    continue
            
            # Finalize totals
            sale.amount_paid = total_paid
            sale.save()
            return redirect('dashboard')
            
    return render(request, 'mims/create_sale.html', {'products': products})