from django import forms
from .models import Sale, SaleItem, Product

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer_name', 'payment_status', 'discount_amount', 'amount_paid']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg', 'placeholder': 'Walk-in Customer'}),
            'payment_status': forms.Select(attrs={'class': 'w-full p-2 border rounded-lg'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded-lg', 'value': 0}),
            'amount_paid': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded-lg', 'value': 0}),
        }