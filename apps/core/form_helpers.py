from django import forms

INPUT = 'input input-bordered w-full'
SELECT = 'select select-bordered w-full'
TEXTAREA = 'textarea textarea-bordered w-full'
MULTISELECT = 'select select-bordered w-full min-h-[8rem]'


def style_form(form):
    """Apply DaisyUI classes to all fields on a form."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.MultiWidget):
            continue
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault('class', 'checkbox checkbox-primary')
        elif isinstance(widget, forms.SelectMultiple):
            widget.attrs.setdefault('class', MULTISELECT)
        elif isinstance(widget, forms.Select):
            widget.attrs.setdefault('class', SELECT)
        elif isinstance(widget, forms.Textarea):
            widget.attrs.setdefault('class', TEXTAREA)
        else:
            widget.attrs.setdefault('class', INPUT)
