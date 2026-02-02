from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Product, Category

class InventoryItemResource(resources.ModelResource):
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'name')
    )

    class Meta:
        model = Product
        fields = ('id', 'name', 'category', 'stock_qty', 'buy_price_per_bulk', 'sell_price_per_base')
        import_id_fields = ('name',) 

    def save_instance(self, instance, is_create, row, type_cleaner=None):
        """
        Custom save logic: If the item already exists (is_create is False), 
        add the new quantity to the existing quantity instead of replacing it.
        """
        if not is_create:
            try:
                # Fetch the current object from DB
                existing_obj = Product.objects.get(name=instance.name)
                # Add imported stock to existing stock
                instance.stock_qty = existing_obj.stock_qty + instance.stock_qty
            except Product.DoesNotExist:
                pass
        super().save_instance(instance, is_create, row, type_cleaner)