# utils.py
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta
from .models import PaymentRecord, Sale, Purchase, Expense

def calculate_sale_totals(sale):
    """
    Calculates subtotal and total_amount.
    Call this whenever a SaleItem is added or modified.
    """
    # Sum up all items (Price * Quantity)
    result = sale.items.aggregate(
        calc_subtotal=Sum(F('quantity_base') * F('price_at_sale'))
    )
    
    sale.subtotal = result['calc_subtotal'] or 0
    sale.total_amount = sale.subtotal - sale.discount_amount
    sale.save(update_fields=['subtotal', 'total_amount'])

def generate_invoice_text(sale):
    """
    Generates a professional text-based invoice.
    """
    header = f"{'PHARMA-LOGIC MEDICAL':^40}\n"
    header += f"{'Inventory & Sales Report':^40}\n"
    header += "="*40 + "\n"
    
    info = (
        f"Invoice ID: {sale.id}\n"
        f"Date:       {sale.sale_date.strftime('%Y-%m-%d %H:%M')}\n"
        f"Customer:   {sale.customer_name or 'General Client'}\n"
        f"Status:     {sale.get_payment_status_display()}\n"
    )
    
    table_head = f"{'-'*40}\n"
    table_head += f"{'Item':<18} {'Qty':<4} {'Price':<7} {'Total':<8}\n"
    
    body = ""
    for item in sale.items.all():
        line_total = item.quantity_base * item.price_at_sale
        body += f"{item.product.name[:17]:<18} {item.quantity_base:<4} {item.price_at_sale:<7} {line_total:<8.2f}\n"
    
    footer = f"{'-'*40}\n"
    footer += f"{'Subtotal:':<30} {sale.subtotal:>8.2f}\n"
    footer += f"{'Discount:':<30} -{sale.discount_amount:>7.2f}\n"
    footer += f"{'GRAND TOTAL:':<30} {sale.total_amount:>8.2f}\n"
    footer += f"{'Amount Paid:':<30} {sale.amount_paid:>8.2f}\n"
    footer += f"{'BALANCE DUE:':<30} {sale.balance_due():>8.2f}\n"
    footer += "="*40
    
    return header + info + table_head + body + footer

def get_financial_report(period='daily'):
    now = timezone.now()
    
    if period == 'daily':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'weekly':
        start_date = now - timedelta(days=now.weekday())
    elif period == 'monthly':
        start_date = now.replace(day=1, hour=0, minute=0, second=0)
    elif period == 'yearly':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0)
    else:
        return None

    # 1. Accrual Revenue (Total value of all sales made)
    revenue_data = Sale.objects.filter(sale_date__gte=start_date).aggregate(
        total_revenue=Sum('total_amount'),
        actual_cash=Sum('amount_paid') # 2. Cash In (Total money actually collected)
    )
    
    total_revenue = revenue_data['total_revenue'] or 0
    total_cash_in = revenue_data['actual_cash'] or 0
    
    # 3. Money Out
    total_purchases = Purchase.objects.filter(purchase_date__gte=start_date).aggregate(
        total=Sum('total_cost'))['total'] or 0
    
    total_expenses = Expense.objects.filter(date__gte=start_date).aggregate(
        total=Sum('amount'))['total'] or 0

    # Calculations
    paper_profit = total_revenue - (total_purchases + total_expenses)
    net_cash_flow = total_cash_in - (total_purchases + total_expenses)
    total_debt = total_revenue - total_cash_in # Money still owed by customers

    return {
        'period': period.capitalize(),
        'revenue': total_revenue,
        'cash_in': total_cash_in,
        'purchases': total_purchases,
        'expenses': total_expenses,
        'paper_profit': paper_profit,
        'cash_flow': net_cash_flow,
        'outstanding_loans': total_debt
    }

def format_report_text(report_data):
    """Formats the dictionary into a readable text summary."""
    if not report_data:
        return "Invalid Report Period."
        
    border = "=" * 40
    return (
        f"{border}\n"
        f"{report_data['period'] + ' FINANCIAL SUMMARY':^40}\n"
        f"Since: {report_data['start_date'].strftime('%Y-%m-%d %H:%M')}\n"
        f"{border}\n"
        f"{'Total Sales:':<25} {report_data['sales']:>12.2f}\n"
        f"{'Total Purchases:':<25} -{report_data['purchases']:>11.2f}\n"
        f"{'Total Expenses:':<25} -{report_data['expenses']:>11.2f}\n"
        f"{'-'*40}\n"
        f"{'NET PROFIT:':<25} {report_data['net_profit']:>12.2f}\n"
        f"{border}"
    )

# Updated snippet for utils.py to use actual payment dates
def get_cash_flow_report(start_date):
    """Calculates actual money collected during a period regardless of sale date."""
    actual_cash_collected = PaymentRecord.objects.filter(
        date_paid__gte=start_date
    ).aggregate(total=Sum('amount_received'))['total'] or 0
    
    return actual_cash_collected