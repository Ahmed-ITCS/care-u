from django import forms

from apps.billing.models import Invoice, Payment
from apps.clinical.models import Visit
from apps.core.form_helpers import style_form


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'method', 'transaction_id', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, invoice=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoice = invoice
        if invoice and not self.instance.pk:
            self.fields['amount'].initial = invoice.balance_due
        style_form(self)

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if self.invoice and amount > self.invoice.balance_due:
            raise forms.ValidationError(f'Amount cannot exceed balance due (PKR {self.invoice.balance_due}).')
        return amount


class InvoiceFromVisitForm(forms.Form):
    visit = forms.ModelChoiceField(
        queryset=Visit.objects.none(),
        label='Visit without invoice',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        invoiced = Invoice.objects.exclude(visit__isnull=True).values_list('visit_id', flat=True)
        self.fields['visit'].queryset = (
            Visit.objects.exclude(pk__in=invoiced)
            .select_related('patient', 'doctor')
            .order_by('-visit_date')
        )
        style_form(self)
