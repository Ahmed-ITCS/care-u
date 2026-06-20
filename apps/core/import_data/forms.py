from django import forms

from apps.core.form_helpers import style_form


class CSVImportForm(forms.Form):
    import_type = forms.ChoiceField(label='Data type')
    csv_file = forms.FileField(
        label='CSV file',
        help_text='UTF-8 CSV with a header row. Max 5 MB.',
        widget=forms.ClearableFileInput(attrs={'accept': '.csv,text/csv'}),
    )

    def __init__(self, *args, import_type_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if import_type_choices:
            self.fields['import_type'].choices = import_type_choices
        style_form(self)

    def clean_csv_file(self):
        f = self.cleaned_data['csv_file']
        if f.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File too large. Maximum size is 5 MB.')
        if not f.name.lower().endswith('.csv'):
            raise forms.ValidationError('Please upload a .csv file.')
        return f
