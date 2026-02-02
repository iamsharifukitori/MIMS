from django.utils import timezone
from datetime import timedelta
from .models import Product

def notifications(request):
    """
    Globally provides notification data to all templates.
    """
    today = timezone.now().date()
    six_months_from_now = today + timedelta(days=180)
    
    # Logic: Stock < 2 OR Expiry Date <= 6 months from today
    low_stock = Product.objects.filter(stock_qty__lt=2)
    expiring_soon = Product.objects.filter(expiry_date__lte=six_months_from_now)
    
    # Combine unique IDs to avoid double-counting the same product
    total_ids = set(low_stock.values_list('id', flat=True)) | set(expiring_soon.values_list('id', flat=True))
    count = len(total_ids)
    
    return {
        'notification_count': count,
        'has_notifications': count > 0
    }