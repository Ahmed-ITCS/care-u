import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.core.import_data.schemas import get_required_keys, normalize_header
from apps.patients.models import Patient
from apps.users.models import Role, StaffProfile, DoctorProfile
from apps.pharmacy.models import Drug, DrugCategory
from apps.laboratory.models import TestCatalog, TestCategory

User = get_user_model()
CNIC_PATTERN = re.compile(r'^\d{5}-\d{7}-\d$')
VALID_GENDERS = {'M', 'F', 'O'}
VALID_BLOOD = {'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'}
VALID_ROLES = {r.value for r in Role if r != Role.PATIENT}


class ImportResult:
    def __init__(self):
        self.created = 0
        self.updated = 0
        self.skipped = 0
        self.errors = []

    def add_error(self, row_num, message):
        self.errors.append({'row': row_num, 'message': message})

    @property
    def success(self):
        return self.created + self.updated


def parse_csv_file(uploaded_file):
    """Read uploaded CSV and return list of row dicts with normalized keys."""
    raw = uploaded_file.read()
    for encoding in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError('Could not read file. Please save as UTF-8 CSV.')

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError('CSV file is empty or has no header row.')

    rows = []
    for row in reader:
        normalized = {}
        for header, value in row.items():
            if header is None:
                continue
            key = normalize_header(header)
            normalized[key] = (value or '').strip()
        if any(normalized.values()):
            rows.append(normalized)
    return rows


def validate_headers(rows, import_type):
    if not rows:
        raise ValueError('No data rows found. Add at least one row below the header.')
    required = set(get_required_keys(import_type))
    present = set(rows[0].keys())
    missing = required - present
    if missing:
        labels = ', '.join(sorted(missing))
        raise ValueError(f'Missing required columns: {labels}')


def _parse_date(value, row_num, field, result):
    if not value:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    result.add_error(row_num, f'{field}: invalid date "{value}" (use YYYY-MM-DD)')
    return None


def _parse_decimal(value, default=Decimal('0')):
    if not value:
        return default
    try:
        return Decimal(value.replace(',', ''))
    except (InvalidOperation, AttributeError):
        return None


@transaction.atomic
def import_patients(rows, user, result):
    from apps.tenants.limits import check_patient_limit, SubscriptionLimitExceeded

    for i, row in enumerate(rows, start=2):
        cnic = row.get('cnic', '')
        if not CNIC_PATTERN.match(cnic):
            result.add_error(i, f'CNIC "{cnic}" must be format 12345-1234567-1')
            continue

        first = row.get('first_name', '')
        last = row.get('last_name', '')
        phone = row.get('phone', '')
        if not first or not last or not phone:
            result.add_error(i, 'first_name, last_name, and phone are required')
            continue

        gender = row.get('gender', '').upper()
        if gender and gender not in VALID_GENDERS:
            result.add_error(i, f'gender must be M, F, or O (got "{gender}")')
            continue

        blood = row.get('blood_group', '')
        if blood and blood not in VALID_BLOOD:
            result.add_error(i, f'blood_group must be A+, B+, etc. (got "{blood}")')
            continue

        dob = _parse_date(row.get('date_of_birth', ''), i, 'date_of_birth', result)
        if row.get('date_of_birth') and dob is None:
            continue

        defaults = {
            'first_name': first,
            'last_name': last,
            'phone': phone,
            'date_of_birth': dob,
            'gender': gender,
            'blood_group': blood,
            'email': row.get('email', ''),
            'address': row.get('address', ''),
            'city': row.get('city') or 'Islamabad',
            'notes': row.get('notes', ''),
            'registered_by': user,
        }

        existing = Patient.all_objects.filter(cnic=cnic).first()
        if existing:
            if existing.is_deleted:
                for k, v in defaults.items():
                    setattr(existing, k, v)
                existing.is_deleted = False
                existing.deleted_at = None
                existing.save()
                result.updated += 1
            else:
                result.add_error(i, f'CNIC {cnic} already registered ({existing.mr_number})')
            continue

        try:
            check_patient_limit()
        except SubscriptionLimitExceeded as exc:
            result.add_error(i, str(exc.detail))
            break

        Patient.objects.create(cnic=cnic, **defaults)
        result.created += 1


@transaction.atomic
def import_staff(rows, user, result):
    from apps.tenants.limits import check_staff_limit, SubscriptionLimitExceeded

    for i, row in enumerate(rows, start=2):
        username = row.get('username', '')
        role = row.get('role', '').lower()
        email = row.get('email', '')
        first = row.get('first_name', '')
        last = row.get('last_name', '')

        if not username or not email or not first or not last:
            result.add_error(i, 'username, first_name, last_name, and email are required')
            continue
        if role not in VALID_ROLES or role == 'admin':
            result.add_error(i, f'role must be one of: doctor, nurse, receptionist, accountant, pharmacist, lab_tech')
            continue

        if User.objects.filter(username=username).exists():
            result.add_error(i, f'Username "{username}" already exists')
            continue

        try:
            check_staff_limit()
        except SubscriptionLimitExceeded as exc:
            result.add_error(i, str(exc.detail))
            break

        password = row.get('password') or 'changeme123'
        new_user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first,
            last_name=last,
            role=role,
            phone=row.get('phone', ''),
            is_verified=True,
        )
        StaffProfile.objects.create(user=new_user, cnic=row.get('cnic', ''))

        if role == Role.DOCTOR:
            specialty = row.get('specialty') or 'General Medicine'
            license_no = row.get('license_number') or f'PMDC-IMPORT-{username.upper()}'
            fee = _parse_decimal(row.get('consultation_fee'), Decimal('2000'))
            DoctorProfile.objects.create(
                user=new_user,
                specialty=specialty,
                license_number=license_no,
                consultation_fee=fee or Decimal('2000'),
            )

        result.created += 1


@transaction.atomic
def import_drugs(rows, user, result):
    for i, row in enumerate(rows, start=2):
        generic = row.get('generic_name', '')
        if not generic:
            result.add_error(i, 'generic_name is required')
            continue

        category_name = row.get('category') or 'General'
        category, _ = DrugCategory.objects.get_or_create(name=category_name)

        price = _parse_decimal(row.get('unit_price'))
        if row.get('unit_price') and price is None:
            result.add_error(i, f'unit_price "{row.get("unit_price")}" is not a valid number')
            continue

        reorder = row.get('reorder_level')
        try:
            reorder_level = int(reorder) if reorder else 10
        except ValueError:
            result.add_error(i, f'reorder_level must be a number')
            continue

        strength = row.get('strength', '')
        drug, created = Drug.objects.get_or_create(
            generic_name=generic,
            strength=strength,
            defaults={
                'category': category,
                'brand_name': row.get('brand_name', ''),
                'form': row.get('form', ''),
                'unit_price': price or Decimal('0'),
                'reorder_level': reorder_level,
            },
        )
        if created:
            result.created += 1
        else:
            result.skipped += 1
            result.add_error(i, f'{generic} {strength} already exists — skipped')


@transaction.atomic
def import_lab_tests(rows, user, result):
    for i, row in enumerate(rows, start=2):
        code = row.get('code', '').upper()
        name = row.get('name', '')
        category_name = row.get('category', '')
        price = _parse_decimal(row.get('price'))

        if not code or not name or not category_name:
            result.add_error(i, 'code, name, and category are required')
            continue
        if price is None:
            result.add_error(i, f'price "{row.get("price")}" is not a valid number')
            continue

        try:
            category = TestCategory.objects.get(name__iexact=category_name)
        except TestCategory.DoesNotExist:
            result.add_error(i, f'category "{category_name}" not found — create it first or run seed data')
            continue

        turnaround = row.get('turnaround_hours')
        try:
            turnaround_hours = int(turnaround) if turnaround else 24
        except ValueError:
            result.add_error(i, 'turnaround_hours must be a number')
            continue

        _, created = TestCatalog.objects.get_or_create(
            code=code,
            defaults={
                'category': category,
                'name': name,
                'price': price,
                'sample_type': row.get('sample_type') or 'blood',
                'turnaround_hours': turnaround_hours,
            },
        )
        if created:
            result.created += 1
        else:
            result.skipped += 1
            result.add_error(i, f'Test code {code} already exists — skipped')


IMPORT_HANDLERS = {
    'patients': import_patients,
    'staff': import_staff,
    'drugs': import_drugs,
    'lab_tests': import_lab_tests,
}


def run_import(import_type, uploaded_file, user):
    result = ImportResult()
    rows = parse_csv_file(uploaded_file)
    validate_headers(rows, import_type)
    handler = IMPORT_HANDLERS[import_type]
    handler(rows, user, result)
    return result
