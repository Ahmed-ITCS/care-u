import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect

from apps.core.import_data.forms import CSVImportForm
from apps.core.import_data.schemas import IMPORT_TYPES, SAMPLE_ROWS, get_columns
from apps.core.import_data.services import run_import
from apps.tenants.middleware import ensure_request_tenant
from apps.tenants.auth import sync_user_to_index


def _allowed_import_types(user):
    types = []
    for key, meta in IMPORT_TYPES.items():
        if user.role == 'admin' or user.role in meta.get('roles', ()):
            types.append((key, meta['label']))
    return types


def _import_context(user, active_type=None, result=None):
    allowed = _allowed_import_types(user)
    if not allowed:
        return None
    type_keys = [t[0] for t in allowed]
    if active_type not in type_keys:
        active_type = type_keys[0]

    schemas = {}
    for key, _ in allowed:
        meta = IMPORT_TYPES[key]
        columns = get_columns(key)
        preview_matrix = [
            [row.get(c['key'], '') for c in columns]
            for row in SAMPLE_ROWS.get(key, [])
        ]
        schemas[key] = {
            'label': meta['label'],
            'description': meta['description'],
            'icon': meta.get('icon', 'file'),
            'columns': columns,
            'sample_rows': SAMPLE_ROWS.get(key, []),
            'preview_matrix': preview_matrix,
        }

    import_tabs = []
    for key, label in allowed:
        meta = IMPORT_TYPES[key]
        import_tabs.append({
            'key': key,
            'label': label,
            'icon': meta.get('icon', 'file'),
        })

    return {
        'allowed_types': allowed,
        'import_tabs': import_tabs,
        'active_type': active_type,
        'schemas': schemas,
        'active_schema': schemas[active_type],
        'form': CSVImportForm(import_type_choices=allowed, initial={'import_type': active_type}),
        'result': result,
    }


@login_required
def data_import(request):
    allowed = _allowed_import_types(request.user)
    if not allowed:
        messages.error(request, 'You do not have permission to import data.')
        return redirect('core:dashboard')

    active_type = request.GET.get('type') or request.POST.get('import_type') or allowed[0][0]
    result = None

    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES, import_type_choices=allowed)
        active_type = request.POST.get('import_type', active_type)
        if form.is_valid():
            import_type = form.cleaned_data['import_type']
            try:
                result = run_import(import_type, form.cleaned_data['csv_file'], request.user)
                if import_type == 'staff' and result.created:
                    tenant = ensure_request_tenant(request)
                    if tenant:
                        from django.contrib.auth import get_user_model
                        User = get_user_model()
                        recent = User.objects.exclude(role='patient').order_by('-date_joined')[:result.created]
                        for u in recent:
                            sync_user_to_index(tenant, u)
                if result.success:
                    messages.success(
                        request,
                        f'Import complete: {result.created} created, {result.updated} updated.',
                    )
                elif result.errors:
                    messages.warning(
                        request,
                        f'Import finished with {len(result.errors)} issue(s). Review details below.',
                    )
                else:
                    messages.info(request, 'No records were imported.')
            except ValueError as exc:
                messages.error(request, str(exc))
                form = CSVImportForm(import_type_choices=allowed, initial={'import_type': active_type})
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = CSVImportForm(import_type_choices=allowed, initial={'import_type': active_type})

    ctx = _import_context(request.user, active_type, result)
    ctx['form'] = form
    return render(request, 'core/data_import.html', ctx)


@login_required
def data_import_sample(request, import_type):
    allowed = dict(_allowed_import_types(request.user))
    if import_type not in allowed:
        messages.error(request, 'Invalid import type.')
        return redirect('core:data_import')

    columns = [c['key'] for c in get_columns(import_type)]
    rows = SAMPLE_ROWS.get(import_type, [])

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{import_type}_sample.csv"'
    return response
