from django.db import connection


def hospital_context(request):
    """TENANT-AWARE: Use current tenant branding or fall back to HospitalConfig."""
    tenant = getattr(connection, 'tenant', None)

    if tenant and getattr(tenant, 'schema_name', 'public') != 'public':
        return {
            'hospital_name': tenant.name,
            'hospital_address': tenant.address,
            'hospital_phone': tenant.phone,
            'hospital_logo': getattr(tenant, 'logo', None),
            'hospital_primary_color': getattr(tenant, 'primary_color', '#1E40AF'),
            'hospital_accent_color': getattr(tenant, 'accent_color', '#059669'),
        }

    # Inside tenant schema but connection.tenant not set — use HospitalConfig
    try:
        from apps.core.models import HospitalConfig
        config = HospitalConfig.load()
        return {
            'hospital_name': config.name,
            'hospital_address': config.address,
            'hospital_phone': config.phone,
        }
    except Exception:
        from django.conf import settings
        return {
            'hospital_name': settings.PLATFORM_NAME,
            'hospital_address': '',
            'hospital_phone': '',
        }


def navigation_context(request):
    if not request.user.is_authenticated:
        return {'nav_items': []}

    from apps.tenants.limits import filter_nav_items, get_active_plan

    role = getattr(request.user, 'role', None)
    nav_map = {
        'admin': [
            {'label': 'Dashboard', 'url': 'core:dashboard', 'icon': 'home'},
            {'label': 'Patients', 'url': 'patients:list', 'icon': 'users'},
            {'label': 'Appointments', 'url': 'appointments:list', 'icon': 'calendar'},
            {'label': 'Clinical', 'url': 'clinical:visits', 'icon': 'stethoscope'},
            {'label': 'Laboratory', 'url': 'laboratory:requests', 'icon': 'flask'},
            {'label': 'Pharmacy', 'url': 'pharmacy:inventory', 'icon': 'pill'},
            {'label': 'Billing', 'url': 'billing:invoices', 'icon': 'receipt'},
            {'label': 'HR', 'url': 'hr:attendance', 'icon': 'briefcase'},
            {'label': 'Reports', 'url': 'reports:index', 'icon': 'chart'},
            {'label': 'Staff', 'url': 'users:staff_list', 'icon': 'user-cog'},
            {'label': 'Settings', 'url': 'tenants:hospital_settings', 'icon': 'cog'},
            {'label': 'Subscription', 'url': 'tenants:billing', 'icon': 'credit-card'},
        ],
        'doctor': [
            {'label': 'Dashboard', 'url': 'core:dashboard', 'icon': 'home'},
            {'label': 'My Appointments', 'url': 'appointments:doctor_calendar', 'icon': 'calendar'},
            {'label': 'Patients', 'url': 'patients:list', 'icon': 'users'},
            {'label': 'Visits', 'url': 'clinical:visits', 'icon': 'stethoscope'},
            {'label': 'Leave', 'url': 'hr:leaves', 'icon': 'briefcase'},
        ],
        'nurse': [
            {'label': 'Dashboard', 'url': 'core:dashboard', 'icon': 'home'},
            {'label': 'Patients', 'url': 'patients:list', 'icon': 'users'},
            {'label': 'Wards', 'url': 'clinical:wards', 'icon': 'bed'},
            {'label': 'Vitals', 'url': 'clinical:vitals', 'icon': 'heart'},
            {'label': 'Leave', 'url': 'hr:leaves', 'icon': 'briefcase'},
        ],
        'receptionist': [
            {'label': 'Dashboard', 'url': 'core:dashboard', 'icon': 'home'},
            {'label': 'Queue', 'url': 'appointments:queue', 'icon': 'list'},
            {'label': 'Appointments', 'url': 'appointments:list', 'icon': 'calendar'},
            {'label': 'Register Patient', 'url': 'patients:register', 'icon': 'user-plus'},
            {'label': 'Leave', 'url': 'hr:leaves', 'icon': 'briefcase'},
        ],
        'accountant': [
            {'label': 'Dashboard', 'url': 'core:dashboard', 'icon': 'home'},
            {'label': 'Invoices', 'url': 'billing:invoices', 'icon': 'receipt'},
            {'label': 'Payments', 'url': 'billing:payments', 'icon': 'credit-card'},
            {'label': 'Reports', 'url': 'reports:index', 'icon': 'chart'},
            {'label': 'Leave', 'url': 'hr:leaves', 'icon': 'briefcase'},
        ],
        'pharmacist': [
            {'label': 'Dashboard', 'url': 'core:dashboard', 'icon': 'home'},
            {'label': 'Inventory', 'url': 'pharmacy:inventory', 'icon': 'pill'},
            {'label': 'Dispense', 'url': 'pharmacy:dispense', 'icon': 'prescription'},
            {'label': 'Purchase Orders', 'url': 'pharmacy:purchase_orders', 'icon': 'shopping-cart'},
            {'label': 'Leave', 'url': 'hr:leaves', 'icon': 'briefcase'},
        ],
        'lab_tech': [
            {'label': 'Dashboard', 'url': 'core:dashboard', 'icon': 'home'},
            {'label': 'Test Requests', 'url': 'laboratory:requests', 'icon': 'flask'},
            {'label': 'Results', 'url': 'laboratory:results', 'icon': 'clipboard'},
            {'label': 'Leave', 'url': 'hr:leaves', 'icon': 'briefcase'},
        ],
        'patient': [
            {'label': 'Dashboard', 'url': 'core:dashboard', 'icon': 'home'},
            {'label': 'My Appointments', 'url': 'appointments:my_appointments', 'icon': 'calendar'},
            {'label': 'My Records', 'url': 'patients:portal', 'icon': 'file'},
            {'label': 'My Bills', 'url': 'billing:my_bills', 'icon': 'receipt'},
        ],
    }
    plan = get_active_plan()
    items = nav_map.get(role, nav_map['admin'])
    return {'nav_items': filter_nav_items(items, plan)}
