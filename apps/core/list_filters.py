from django import forms

# DaisyUI classes applied directly — never use "filter-*" prefix (Tailwind strips those)
INPUT_CLS = 'input input-bordered input-sm w-full h-9 min-h-9 text-sm bg-base-100'
SELECT_CLS = 'select select-bordered select-sm w-full h-9 min-h-9 text-sm bg-base-100'
SEARCH_CLS = INPUT_CLS + ' pl-9'
CHECKBOX_CLS = 'checkbox checkbox-primary checkbox-sm'


def style_filter_form(form):
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault('class', CHECKBOX_CLS)
        elif isinstance(widget, forms.Select):
            widget.attrs.setdefault('class', SELECT_CLS)
        elif field.label in ('Search', 'Patient'):
            widget.attrs.setdefault('class', SEARCH_CLS)
            widget.attrs.setdefault('placeholder', 'Name, MR number, CNIC, phone…')
        else:
            widget.attrs.setdefault('class', INPUT_CLS)
            if not widget.attrs.get('placeholder') and field.label:
                widget.attrs.setdefault('placeholder', str(field.label))
    return form


def _layout_for(filter_class):
    return getattr(filter_class, 'layout', None) or {
        'primary': list(filter_class.base_filters.keys()),
        'groups': [],
    }


def _split_form_fields(form, layout):
    primary = []
    advanced_groups = []
    used = set()

    for name in layout.get('primary', []):
        if name in form.fields:
            primary.append(form[name])
            used.add(name)

    for group in layout.get('groups', []):
        fields = []
        for name in group.get('fields', []):
            if name in form.fields and name not in used:
                fields.append(form[name])
                used.add(name)
        if fields:
            advanced_groups.append({'label': group.get('label', 'More'), 'fields': fields})

    for name, field in form.fields.items():
        if name not in used:
            if not advanced_groups:
                advanced_groups.append({'label': 'More', 'fields': []})
            advanced_groups[-1]['fields'].append(field)

    return primary, advanced_groups


def apply_list_filters(request, queryset, filter_class, limit=None, exclude_fields=()):
    filter_set = filter_class(request.GET, queryset=queryset)
    qs = filter_set.qs
    if limit is not None:
        qs = qs[:limit]
    form = style_filter_form(filter_set.form)
    for name in exclude_fields:
        form.fields.pop(name, None)
    layout = _layout_for(filter_class)
    primary_fields, advanced_groups = _split_form_fields(form, layout)
    return qs, form, primary_fields, advanced_groups


def filter_list_context(request, queryset, filter_class, limit=None, exclude_fields=(), clear_url=''):
    qs, form, primary, advanced = apply_list_filters(
        request, queryset, filter_class, limit=limit, exclude_fields=exclude_fields,
    )
    advanced_active = filters_active(request) and any(
        field.html_name in request.GET and request.GET.get(field.html_name)
        for group in advanced for field in group['fields']
    )
    return {
        'items': qs,
        'filter_form': form,
        'filter_primary': primary,
        'filter_advanced': advanced,
        'filters_active': filters_active(request),
        'filters_advanced_active': advanced_active,
        'clear_filters_url': clear_url,
    }


def filters_active(request, exclude=('page',)):
    return any(k not in exclude and v for k, v in request.GET.items())
