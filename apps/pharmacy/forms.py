from django import forms

from apps.core.form_helpers import style_form
from apps.pharmacy.models import Drug, DrugCategory, Supplier, PurchaseOrder


class DrugForm(forms.ModelForm):
    class Meta:
        model = Drug
        fields = [
            'category', 'generic_name', 'brand_name', 'strength', 'form',
            'unit_price', 'reorder_level', 'barcode',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Supplier.objects.all().order_by('name')
        style_form(self)
