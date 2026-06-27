import re

from django import forms
from django.forms import widgets
from django.utils.html import format_html
from django.utils.safestring import mark_safe

DEFAULT_COUNTRY_CODE = '+92'

# Common codes for regional hospitals; PK first as default.
PHONE_COUNTRY_CHOICES = [
    ('+92', 'PK +92'),
    ('+93', 'AF +93'),
    ('+91', 'IN +91'),
    ('+880', 'BD +880'),
    ('+94', 'LK +94'),
    ('+977', 'NP +977'),
    ('+971', 'AE +971'),
    ('+966', 'SA +966'),
    ('+974', 'QA +974'),
    ('+968', 'OM +968'),
    ('+965', 'KW +965'),
    ('+973', 'BH +973'),
    ('+98', 'IR +98'),
    ('+90', 'TR +90'),
    ('+44', 'GB +44'),
    ('+1', 'US +1'),
    ('+61', 'AU +61'),
    ('+49', 'DE +49'),
    ('+33', 'FR +33'),
    ('+86', 'CN +86'),
]

_COUNTRY_CODES = sorted((code for code, _ in PHONE_COUNTRY_CHOICES), key=len, reverse=True)


def split_phone(value):
    """Split stored phone into (country_code, local_number) for form display."""
    if not value:
        return DEFAULT_COUNTRY_CODE, ''

    value = str(value).strip()
    if value.startswith('+'):
        for code in _COUNTRY_CODES:
            if value.startswith(code):
                local = re.sub(r'\D', '', value[len(code):])
                if code == DEFAULT_COUNTRY_CODE and local and not local.startswith('0'):
                    local = f'0{local}'
                return code, local
        return DEFAULT_COUNTRY_CODE, re.sub(r'\D', '', value.lstrip('+'))

    digits = re.sub(r'\D', '', value)
    if digits.startswith('0'):
        return DEFAULT_COUNTRY_CODE, digits
    return DEFAULT_COUNTRY_CODE, digits


def format_phone(country_code, local):
    """Normalize country code + local number for storage."""
    local = re.sub(r'\D', '', str(local or '').strip())
    if not local:
        raise forms.ValidationError('Phone number is required.')

    if country_code == DEFAULT_COUNTRY_CODE:
        if local.startswith('0'):
            if len(local) != 11 or local[1] != '3':
                raise forms.ValidationError('Enter a valid Pakistani mobile number (e.g. 03001234567).')
            return local
        if len(local) == 10 and local.startswith('3'):
            return f'0{local}'
        raise forms.ValidationError('Enter a valid Pakistani mobile number (e.g. 3001234567).')

    if len(local) < 6 or len(local) > 15:
        raise forms.ValidationError('Enter a valid phone number.')
    return f'{country_code}{local}'


class PhoneInputWidget(widgets.MultiWidget):
    def __init__(self, attrs=None):
        super().__init__(
            [
                widgets.Select(
                    choices=PHONE_COUNTRY_CHOICES,
                    attrs={
                        'class': 'select select-bordered w-full',
                        'data-phone-country': '',
                    },
                ),
                widgets.TextInput(
                    attrs={
                        'class': 'input input-bordered w-full',
                        'data-phone-local': '',
                        'inputmode': 'tel',
                        'autocomplete': 'tel-national',
                        'placeholder': '3001234567',
                    },
                ),
            ],
            attrs,
        )

    def decompress(self, value):
        return split_phone(value)

    def render(self, name, value, attrs=None, renderer=None):
        if self.is_localized:
            value = self.format_value(value)
        final_attrs = self.build_attrs(self.attrs, attrs)
        id_ = final_attrs.get('id')
        decompressed = self.decompress(value)
        rendered = []
        for index, widget in enumerate(self.widgets):
            widget_name = f'{name}_{index}'
            widget_value = decompressed[index] if index < len(decompressed) else None
            widget_attrs = final_attrs.copy()
            if id_:
                widget_attrs['id'] = f'{id}_{index}'
            rendered.append(widget.render(widget_name, widget_value, widget_attrs, renderer))
        return format_html(
            '<div class="flex gap-2 w-full phone-input-group">'
            '<div class="w-32 shrink-0">{}</div>'
            '<div class="flex-1 min-w-0">{}</div>'
            '</div>',
            mark_safe(rendered[0]),
            mark_safe(rendered[1]),
        )


class PhoneField(forms.MultiValueField):
    widget = PhoneInputWidget

    def __init__(self, *args, **kwargs):
        fields = (
            forms.ChoiceField(choices=PHONE_COUNTRY_CHOICES),
            forms.CharField(max_length=15),
        )
        kwargs.setdefault('label', 'Phone')
        super().__init__(fields, require_all_fields=False, *args, **kwargs)

    def compress(self, data_list):
        if not data_list:
            return ''
        country_code, local = data_list
        return format_phone(country_code, local)
