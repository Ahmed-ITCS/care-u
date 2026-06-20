"""
Subscription plan limits — staff/patient caps and module access.
"""
from django.db import connection
from rest_framework.exceptions import PermissionDenied


class SubscriptionLimitExceeded(PermissionDenied):
    default_detail = 'Subscription limit reached.'


# Modules included in every plan (administration, dashboard, alerts).
BASE_MODULES = frozenset({'core', 'users', 'notifications'})

CORE_PLAN_MODULES = BASE_MODULES | frozenset({'patients', 'appointments', 'clinical', 'billing'})

ALL_PLAN_MODULES = CORE_PLAN_MODULES | frozenset({'laboratory', 'pharmacy', 'hr', 'reports'})

MODULE_LABELS = {
    'patients': 'Patients',
    'appointments': 'Appointments',
    'clinical': 'Clinical',
    'billing': 'Billing',
    'laboratory': 'Laboratory',
    'pharmacy': 'Pharmacy',
    'hr': 'HR',
    'reports': 'Reports',
    'users': 'Staff management',
    'notifications': 'Notifications',
    'core': 'Dashboard',
    'import': 'Import Data',
}

WEB_NAMESPACE_MODULES = {
    'patients': 'patients',
    'appointments': 'appointments',
    'clinical': 'clinical',
    'billing': 'billing',
    'laboratory': 'laboratory',
    'pharmacy': 'pharmacy',
    'hr': 'hr',
    'reports': 'reports',
    'users': 'users',
    'notifications': 'notifications',
    'core': 'core',
    'import': 'core',
}

API_SEGMENT_MODULES = {
    'patients': 'patients',
    'insurance-providers': 'patients',
    'allergies': 'patients',
    'vitals': 'patients',
    'patient-documents': 'patients',
    'users': 'users',
    'staff-profiles': 'users',
    'doctors': 'users',
    'departments': 'core',
    'dashboard': 'core',
    'appointment-types': 'appointments',
    'appointments': 'appointments',
    'doctor-schedules': 'appointments',
    'queue': 'appointments',
    'visits': 'clinical',
    'wards': 'clinical',
    'beds': 'clinical',
    'prescriptions': 'clinical',
    'admissions': 'clinical',
    'lab-tests': 'laboratory',
    'lab-requests': 'laboratory',
    'drugs': 'pharmacy',
    'dispenses': 'pharmacy',
    'purchase-orders': 'pharmacy',
    'suppliers': 'pharmacy',
    'services': 'billing',
    'invoices': 'billing',
    'payments': 'billing',
    'shifts': 'hr',
    'attendance': 'hr',
    'leave-requests': 'hr',
    'payroll': 'hr',
    'notifications': 'notifications',
    'auth': None,
    'me': None,
}


def get_current_hospital():
    tenant = getattr(connection, 'tenant', None)
    if not tenant or getattr(tenant, 'schema_name', 'public') == 'public':
        return None
    return tenant


def get_active_plan(hospital=None):
    hospital = hospital or get_current_hospital()
    if not hospital:
        return None
    from apps.tenants.models import Hospital

    return Hospital.objects.select_related('plan').get(pk=hospital.pk).plan


def resolve_allowed_modules(plan):
    if not plan:
        return ALL_PLAN_MODULES

    modules = (plan.features or {}).get('modules', 'all')
    if modules == 'all':
        return ALL_PLAN_MODULES
    if modules == 'core':
        return CORE_PLAN_MODULES
    if isinstance(modules, list):
        return CORE_PLAN_MODULES | frozenset(modules)
    return ALL_PLAN_MODULES


def plan_module_summary(plan):
    """Human-readable module list for pricing/admin UI."""
    allowed = resolve_allowed_modules(plan)
    premium = allowed - CORE_PLAN_MODULES
    if not premium and allowed >= CORE_PLAN_MODULES:
        return 'Core ERP modules'
    if allowed >= ALL_PLAN_MODULES:
        return 'All ERP modules'
    names = [MODULE_LABELS.get(m, m.title()) for m in sorted(allowed - BASE_MODULES)]
    return ', '.join(names) if names else 'Core ERP modules'


def is_module_allowed(plan, module_name):
    if not module_name or module_name in BASE_MODULES:
        return True
    return module_name in resolve_allowed_modules(plan)


def get_relative_tenant_path(request):
    path = request.path.lstrip('/')
    parts = path.split('/')
    if len(parts) >= 2 and parts[0] == 'h':
        return '/'.join(parts[2:])
    return path


# Paths always allowed inside a tenant (billing, onboarding, dev tools).
EXEMPT_TENANT_PATH_PREFIXES = (
    'static/',
    'media/',
    'admin/',
    'onboarding/',
    'subscription/',
    '__debug__/',
)


def module_for_path(relative_path):
    if not relative_path:
        return 'core'
    if relative_path.startswith(EXEMPT_TENANT_PATH_PREFIXES):
        return None
    if relative_path.startswith('api/v1/'):
        segments = relative_path.split('/')
        if len(segments) >= 3:
            return API_SEGMENT_MODULES.get(segments[2], segments[2])
        return 'core'
    first = relative_path.split('/')[0]
    return WEB_NAMESPACE_MODULES.get(first, first)


def nav_item_module(nav_item):
    url_name = nav_item.get('url', '')
    namespace = url_name.split(':')[0] if ':' in url_name else url_name
    return WEB_NAMESPACE_MODULES.get(namespace, namespace)


def filter_nav_items(nav_items, plan):
    return [item for item in nav_items if is_module_allowed(plan, nav_item_module(item))]


def count_staff():
    from apps.users.models import User

    return User.objects.exclude(role='patient').count()


def count_patients():
    from apps.patients.models import Patient

    return Patient.objects.count()


def get_usage_stats(plan=None):
    plan = plan or get_active_plan()
    return {
        'staff': count_staff(),
        'patients': count_patients(),
        'staff_limit': plan.max_users if plan else None,
        'patients_limit': plan.max_patients if plan else None,
        'allowed_modules': resolve_allowed_modules(plan),
    }


def check_staff_limit(hospital=None):
    plan = get_active_plan(hospital)
    if not plan:
        return
    current = count_staff()
    if current >= plan.max_users:
        raise SubscriptionLimitExceeded(
            f'Staff limit reached ({current}/{plan.max_users}). '
            'Upgrade your subscription plan to add more staff users.'
        )


def check_patient_limit(hospital=None):
    plan = get_active_plan(hospital)
    if not plan:
        return
    current = count_patients()
    if current >= plan.max_patients:
        raise SubscriptionLimitExceeded(
            f'Patient limit reached ({current}/{plan.max_patients}). '
            'Upgrade your subscription plan to register more patients.'
        )


def check_module_access(request):
    hospital = get_current_hospital()
    if not hospital:
        return

    relative = get_relative_tenant_path(request)
    if relative.startswith(EXEMPT_TENANT_PATH_PREFIXES):
        return

    module = module_for_path(relative)
    if module is None:
        return

    plan = get_active_plan(hospital)
    if not is_module_allowed(plan, module):
        label = MODULE_LABELS.get(module, module.replace('_', ' ').title())
        raise SubscriptionLimitExceeded(
            f'The {label} module is not included in your current plan ({plan.display_name}). '
            'Contact your administrator to upgrade.'
        )
