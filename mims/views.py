from django.shortcuts import render, redirect
from django.db.models import Sum, F
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse
from datetime import timedelta
import csv
import io
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from .models import PaymentRecord, Sale, SaleItem, Product, Expense, Purchase, Category
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
import re
from datetime import datetime
from django.shortcuts import get_object_or_404
from .models import Sale,SaleItem

# REMOVED @login_required HERE because this is a helper function, not a view.
def parse_smart_date(date_str):
    """
    Parses messy dates including:
    - 2028-30-06 (Year-Day-Month)
    - 07/27 or 07,2027 (Month/Year -> converts to 1st of month)
    - Standard formats
    """
    if not date_str:
        return None

    # 1. Clean up strings (remove quotes, extra spaces)
    date_str = str(date_str).strip().replace('"', '').replace("'", "")

    # 2. Handle Month/Year formats (e.g., 7/27, 07/2027, 07,27)
    month_year_match = re.match(r'^(\d{1,2})[./,-](\d{2}|\d{4})$', date_str)
    
    if month_year_match:
        month, year = month_year_match.groups()
        if len(year) == 2:
            year = f"20{year}"
        date_str = f"{year}-{month.zfill(2)}-01"
        
    # 3. Try parsing with various formats
    formats = [
        '%Y-%m-%d',  # Standard: 2028-06-30
        '%Y-%d-%m',  # THE FIX FOR YOUR ERROR: 2028-30-06
        '%d-%m-%Y',  # TZ/UK: 30-06-2028
        '%m/%d/%Y',  # US: 06/30/2028
        '%d/%m/%Y',  # Standard Slashes
        '%Y/%m/%d',  # ISO Slashes
        '%d.%m.%Y',  # Dot separator
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    # 4. If all fail, return None
    return None


@login_required
def dashboard_stats(request): 
    return render(request, 'dashboard.html')

@login_required
def dashboard_view(request):
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    daily_revenue = Sale.objects.filter(sale_date__date=today).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    todays_expense_list = Expense.objects.filter(date=today).order_by('-id')
    today_expenses = Expense.objects.filter(date=today).aggregate(Sum('amount'))['amount__sum'] or 0
    daily_profit = SaleItem.objects.filter(sale__sale_date__date=today).aggregate(
        total_profit=Sum(
            (F('price_at_sale') - F('product__buy_price_per_bulk')) * F('quantity_base')
        )
    )['total_profit'] or 0

    most_moving = SaleItem.objects.values('product__name').annotate(total=Sum('quantity_base')).order_by('-total').first()
    top_movers = SaleItem.objects.values('product__name').annotate(total=Sum('quantity_base')).order_by('-total')[:5]
    most_moving = top_movers[0] if top_movers else None
    daily_revenue = Sale.objects.filter(sale_date__date=today).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    daily_revenue = Sale.objects.filter(sale_date__date=today).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    today_expenses = Expense.objects.filter(date=today).aggregate(Sum('amount'))['amount__sum'] or 0

    daily_profit = SaleItem.objects.filter(sale__sale_date__date=today).aggregate(
    total_profit=Sum(
        (F('price_at_sale') - F('product__buy_price_per_bulk')) * F('quantity_base')
            )
        )['total_profit'] or 0
    top_movers = SaleItem.objects.values('product__name').annotate(
        total_sold=Sum('quantity_base')
    ).order_by('-total_sold')[:5]
    least_movers = SaleItem.objects.values('product__name').annotate(
        total_sold=Sum('quantity_base')
    ).order_by('total_sold')[:5]
    today_expenses = Expense.objects.filter(date=today).aggregate(Sum('amount'))['amount__sum'] or 0

        # Net Profit = (Sales Revenue - Cost of Goods Sold) - Expenses
    net_profit = float(daily_profit) - float(today_expenses)

    most_profitable = Product.objects.annotate(
        profit=F('sell_price_per_base') - F('buy_price_per_bulk')
    ).order_by('-profit').first()

    graph_labels = []
    expense_data = []
    profit_data = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        exp = Expense.objects.filter(date=day).aggregate(t=Sum('amount'))['t'] or 0
        prof = SaleItem.objects.filter(sale__sale_date__date=day).aggregate(
            p=Sum((F('price_at_sale') - F('product__buy_price_per_bulk')) * F('quantity_base'))
        )['p'] or 0
        graph_labels.append(day.strftime('%a')) 
        expense_data.append(float(exp))
        profit_data.append(float(prof))

    context = {
        'daily_revenue': daily_revenue,
        'daily_profit': daily_profit, 
        'graph_labels': graph_labels,
        'expense_data': expense_data,
        'profit_data': profit_data,   
        'active_loans': Sale.objects.filter(total_amount__gt=F('amount_paid')).count(),
        'today_expenses': today_expenses,
        'net_profit': net_profit,
        'top_movers': top_movers,
        'least_movers': least_movers,
        'most_moving': top_movers[0] if top_movers else None,
        'todays_expense_list': todays_expense_list,
    }
    
    return render(request, 'mims/dashboard.html', context)

@login_required
def sale_ledger_view(request):
    """Lists last 50 sales with pagination of 10."""
    sale_list = Sale.objects.all().order_by('-sale_date')[:50]
    paginator = Paginator(sale_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {'page_obj': page_obj}
    
    return render(request, 'mims/sale_ledger.html', context)

@login_required
def pay_debt_view(request, sale_id):
    sale = Sale.objects.get(pk=sale_id)
    if request.method == "POST":
        try:
            amount = Decimal(request.POST.get('amount_to_pay', 0))
            if amount > sale.balance_due:
                messages.error(request, f"Error: Payment (Tsh {amount}) exceeds balance (Tsh {sale.balance_due}).")
            elif amount <= 0:
                messages.error(request, "Please enter a valid amount.")
            else:
                PaymentRecord.objects.create(
                    sale=sale,
                    amount_received=amount,
                    note=request.POST.get('note', 'Installment payment')
                )
                messages.success(request, f"Payment of Tsh {amount:,.2f} recorded.")
        except InvalidOperation:
            messages.error(request, "Invalid amount entered.")
        return redirect('sale_ledger')
    
    context = {'sale': sale}
    
    return render(request, 'mims/pay_debt.html', context)

@login_required
def inventory_list_view(request):
    # --- 1. DOWNLOAD TEMPLATE ---
    if request.GET.get('download_template'):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="inventory_template.csv"'
        writer = csv.writer(response)
        # Updated header to 'Items per Box'
        writer.writerow(['ProductName', 'Category', 'CurrentStock', 'RetailPrice', 'BuyingPrice', 'Items per Box', 'BulkUnit', 'BaseUnit', 'ExpiryDate'])
        writer.writerow(['Paracetamol', 'Medicine', '10', '500', '200', '100', 'Box', 'Tablet', '2026-12-31'])
        return response

    if request.method == "POST":
        # --- 2. HANDLE MANUAL PRODUCT ADDITION ---
        if 'add_product' in request.POST:
            try:
                # Use smart parser for manual entry too, just in case
                expiry = parse_smart_date(request.POST.get('expiry_date'))

                Product.objects.create(
                    name=request.POST.get('name'),
                    category_id=request.POST.get('category'),
                    stock_qty=float(request.POST.get('stock_qty', 0)),
                    bulk_unit=request.POST.get('bulk_unit', 'Box'),
                    base_unit=request.POST.get('base_unit', 'Piece'),
                    conversion_factor=int(request.POST.get('conversion_factor', 1)),
                    buy_price_per_bulk=Decimal(request.POST.get('buy_price', 0)),
                    sell_price_per_base=Decimal(request.POST.get('sell_price', 0)),
                    expiry_date=expiry
                )
                messages.success(request, f"Product '{request.POST.get('name')}' saved successfully.")
            except Exception as e:
                messages.error(request, f"Error adding product: {str(e)}")
            return redirect('inventory')

        # --- 3. HANDLE CSV IMPORT ---
        elif 'csv_file' in request.FILES:
            try:
                csv_file = request.FILES['csv_file']
                data_set = csv_file.read().decode('UTF-8')
                io_string = io.StringIO(data_set)
                reader = csv.DictReader(io_string)
                field_map = {name.strip().lower(): name for name in reader.fieldnames}
                
                imported_count = 0
                for row in reader:
                    def get_val(target):
                        for k, v in field_map.items():
                            if target in k: return row.get(v, '').strip()
                        return ''
                    
                    def clean_dec(v): 
                        if not v: return Decimal(0)
                        return Decimal(str(v).replace('$', '').replace(',', '').replace('Tsh', '').strip())
                    
                    def clean_int(v):
                        if not v: return 0
                        return int(float(str(v).replace(',', '').strip()))

                    prod_name = get_val('productname') or row.get('ProductName', '').strip()
                    if not prod_name: continue
                    
                    category, _ = Category.objects.get_or_create(name=get_val('category') or 'General')
                    stock_in = clean_int(get_val('currentstock'))
                    retail = clean_dec(get_val('retail'))
                    buying = clean_dec(get_val('buying')) 
                    
                    # Check for 'items per box' OR 'conversion'
                    conv = clean_int(get_val('conversion')) or clean_int(get_val('items per box')) or 1
                    
                    # --- UPDATED DATE HANDLING ---
                    raw_expiry = get_val('expiry') or get_val('date')
                    expiry = parse_smart_date(raw_expiry) # Uses the robust parser now

                    product = Product.objects.filter(name__iexact=prod_name).first()
                    if product:
                        product.stock_qty += stock_in
                        if buying > 0: product.buy_price_per_bulk = buying
                        if retail > 0: product.sell_price_per_base = retail
                        if expiry: product.expiry_date = expiry
                        product.save()
                    else:
                        Product.objects.create(
                            name=prod_name, 
                            category=category, 
                            stock_qty=stock_in,
                            buy_price_per_bulk=buying, 
                            sell_price_per_base=retail,
                            conversion_factor=conv,
                            bulk_unit=get_val('bulkunit') or 'Box',
                            base_unit=get_val('baseunit') or 'Item',
                            expiry_date=expiry
                        )
                    imported_count += 1
                messages.success(request, f"Imported {imported_count} items.")
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
            return redirect('inventory')

    # --- 4. VIEW RENDER ---
    products = Product.objects.select_related('category').all().order_by('name')
    categories = Category.objects.all()
    inventory_data = []
    total_valuation = Decimal(0)

    for p in products:
        # Check if stock_value is a callable method or a property
        val = p.stock_value() if callable(getattr(p, 'stock_value', None)) else getattr(p, 'stock_value', 0)
        total_valuation += Decimal(val)
        
        # FIX: Calculate total pieces for template display
        total_pieces = p.stock_qty * p.conversion_factor
        
        inventory_data.append({
            'item': p,
            'stock_value_display': f"{val:,.2f}", 
            'retail_price_display': f"{p.sell_price_per_base:,.2f}", 
            'stock_qty_display': f"{p.stock_qty:,}", 
            'is_low_stock': p.stock_qty < 2,
            'total_pieces': total_pieces # Added so template can see it
        })

    context = {
        'inventory': inventory_data,
        'total_valuation': f"{total_valuation:,.2f}",
        'categories': categories
    }

    return render(request, 'mims/inventory.html', context)

@login_required
def expense_list_view(request):
    if request.method == "POST":
        description = request.POST.get('description')
        amount = request.POST.get('amount')
        date = request.POST.get('date') or timezone.now().date()
        
        if description and amount:
            Expense.objects.create(description=description, amount=amount, date=date)
            return redirect('expense_list')

    expenses = Expense.objects.all().order_by('-date')
    today_total = Expense.objects.filter(date=timezone.now().date()).aggregate(Sum('amount'))['amount__sum'] or 0
    
    return render(request, 'mims/expenses.html', {
        'expenses': expenses,
        'today_total': today_total,
    })

@login_required
def create_sale_view(request):
    products = Product.objects.all()
    if request.method == 'POST':
        p_names = request.POST.getlist('product_name[]')
        qtys = request.POST.getlist('quantity[]')
        customer = request.POST.get('customer_name', '').strip()
        initial_payment = Decimal(request.POST.get('amount_paid', 0))

        if p_names:
            sale = Sale.objects.create(
                customer_name=customer if customer else "Walk-in",
                amount_paid=initial_payment,
                sale_date=timezone.now()
            )
            
            for name, qty in zip(p_names, qtys):
                try:
                    p = Product.objects.get(name=name)
                    SaleItem.objects.create(
                        sale=sale, 
                        product=p, 
                        quantity_base=int(qty), 
                        price_at_sale=p.sell_price_per_base
                    )
                except (Product.DoesNotExist, ValueError): 
                    continue
            
            sale.update_status()
            
            if sale.payment_status != 'PAID' and sale.customer_name == "Walk-in":
                messages.error(request, "Customer Name is required for Loan/Partial sales.")
                sale.delete()
                return redirect('create_sale')

            messages.success(request, f"Sale processed successfully.")
            return redirect('dashboard')
            
    context = {'products': products}
            
    return render(request, 'mims/create_sale.html', context)

@login_required
def notifications_view(request):
    """Generates a filtered list for Purchase Orders or Expired Disposal."""
    today = timezone.now().date()
    six_months = today + timedelta(days=180)
    alert_type = request.GET.get('type')
    
    if alert_type == 'expired':
        # Only products that are actually expired
        alert_items = Product.objects.filter(expiry_date__lt=today).order_by('expiry_date')
    else:
        # Purchase Order: Low stock OR Expiring within 6 months
        from django.db.models import Q
        alert_items = Product.objects.filter(
            Q(stock_qty__lt=2) | Q(expiry_date__lte=six_months)
        ).distinct().order_by('name')
    
    context = {
        'alert_items': alert_items,
        'today': today,
    }
    return render(request, 'mims/purchase_order.html', context)

@login_required
def view_sale_view(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    today = timezone.now().date()
    
    # FIX: Consolidated definitions into one variable to prevent overwriting calculation
    sale_items = SaleItem.objects.filter(sale=sale).annotate(
        subtotal=F('price_at_sale') * F('quantity_base')
    )
    
    # Calculate Sale Total
    today_total = sale_items.aggregate(
        total=Sum(F('price_at_sale') * F('quantity_base'))
    )['total'] or 0

    # Calculate Daily Expenses
    today_expenses = Expense.objects.filter(date=today).aggregate(
        total=Sum('amount')
    )['total'] or 0

    context = {
        'sale': sale,
        'sale_items': sale_items,
        'today_total': today_total,
        'today_expenses': today_expenses,
    }
    return render(request, 'mims/view_sale.html', context)

@login_required
def edit_product_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all()
    
    if request.method == "POST":
        try:
            product.name = request.POST.get('name')
            product.category_id = request.POST.get('category')
            product.stock_qty = float(request.POST.get('stock_qty', 0))
            product.bulk_unit = request.POST.get('bulk_unit')
            product.base_unit = request.POST.get('base_unit')
            product.conversion_factor = int(request.POST.get('conversion_factor', 1))
            product.buy_price_per_bulk = Decimal(request.POST.get('buy_price', 0))
            product.sell_price_per_base = Decimal(request.POST.get('sell_price', 0))
            
            expiry_raw = request.POST.get('expiry_date')
            product.expiry_date = parse_smart_date(expiry_raw)
            
            product.save()
            messages.success(request, f"Updated {product.name} successfully.")
            return redirect('inventory')
        except Exception as e:
            messages.error(request, f"Update failed: {str(e)}")
            
    return render(request, 'mims/edit_product.html', {'product': product, 'categories': categories})
@login_required
def loans_list_view(request):
    """Displays only sales with outstanding balances."""
    loans = Sale.objects.filter(
        total_amount__gt=F('amount_paid')
    ).order_by('-sale_date')

    total_outstanding = 0
    for loan in loans:
        total_outstanding += (loan.total_amount - loan.amount_paid)

    context = {
        'loans': loans,
        'total_outstanding': total_outstanding,
    }
    return render(request, 'mims/loans_list.html', context)

@login_required
def barcode_lookup(request):
    barcode = request.GET.get('barcode')
    # Look for the product and return its details as a dictionary
    product = Product.objects.filter(barcode=barcode).first()
    
    if product:
        return JsonResponse({
            'status': 'success',
            'data': {
                'name': product.name,
                'category': product.category.id if product.category else '',
                'bulk_unit': product.bulk_unit,
                'base_unit': product.base_unit,
                'conv': product.conversion_factor,
                'buy': str(product.buy_price_per_bulk),
                'sell': str(product.sell_price_per_base),
            }
        })
    return JsonResponse({'status': 'not_found'})