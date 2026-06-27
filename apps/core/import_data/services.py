import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.core.cnic import format_cnic, is_valid_cnic
from apps.core.import_data.schemas import get_required_keys, normalize_header
from apps.patients.models import Patient
from apps.users.models import Role, StaffProfile, DoctorProfile
from apps.pharmacy.models import Drug, DrugCategory
from apps.laboratory.models import TestCatalog, TestCategory

User = get_user_model()
VALID_GENDERS = {'M', 'F', 'O'}
VALID_BLOOD = {'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'}
VALID_ROLES = {r.value for r in Role if r != Role.PATIENT}
VALID_WARD_TYPES = {'general', 'icu', 'pediatric', 'maternity', 'private', 'emergency'}


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


def _parse_time(value, row_num, field, result):
    if not value:
        result.add_error(row_num, f'{field} is required')
        return None
    for fmt in ('%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M%p'):
        try:
            return datetime.strptime(value.strip(), fmt).time()
        except ValueError:
            continue
    result.add_error(row_num, f'{field}: invalid time "{value}" (use HH:MM)')
    return None


def _parse_bool(value, default=True):
    if not value:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'y', 'active')


@transaction.atomic
def import_patients(rows, user, result):
    from apps.tenants.limits import check_patient_limit, SubscriptionLimitExceeded

    for i, row in enumerate(rows, start=2):
        cnic = format_cnic(row.get('cnic', ''))
        if not is_valid_cnic(cnic):
            result.add_error(i, f'CNIC "{row.get("cnic")}" must be a valid 13-digit CNIC')
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
        StaffProfile.objects.create(user=new_user, cnic=format_cnic(row.get('cnic', '')) or row.get('cnic', ''))

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

        category, _ = TestCategory.objects.get_or_create(name=category_name)

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


@transaction.atomic
def import_wards(rows, user, result):
    from apps.clinical.models import Ward

    for i, row in enumerate(rows, start=2):
        name = row.get('name', '')
        if not name:
            result.add_error(i, 'name is required')
            continue

        ward_type = (row.get('ward_type') or 'general').lower()
        if ward_type not in VALID_WARD_TYPES:
            result.add_error(i, f'ward_type must be one of: {", ".join(sorted(VALID_WARD_TYPES))}')
            continue

        capacity = row.get('capacity')
        try:
            capacity_val = int(capacity) if capacity else 0
        except ValueError:
            result.add_error(i, 'capacity must be a number')
            continue

        ward, created = Ward.objects.get_or_create(
            name=name,
            defaults={
                'ward_type': ward_type,
                'floor': row.get('floor', ''),
                'capacity': capacity_val,
            },
        )
        if created:
            result.created += 1
        else:
            ward.ward_type = ward_type
            ward.floor = row.get('floor', '')
            ward.capacity = capacity_val
            ward.is_active = True
            ward.save(update_fields=['ward_type', 'floor', 'capacity', 'is_active', 'updated_at'])
            result.updated += 1


@transaction.atomic
def import_shifts(rows, user, result):
    from apps.hr.models import Shift

    for i, row in enumerate(rows, start=2):
        name = row.get('name', '')
        if not name:
            result.add_error(i, 'name is required')
            continue

        start_time = _parse_time(row.get('start_time', ''), i, 'start_time', result)
        if start_time is None:
            continue
        end_time = _parse_time(row.get('end_time', ''), i, 'end_time', result)
        if end_time is None:
            continue

        is_active = _parse_bool(row.get('is_active'), default=True)
        shift, created = Shift.objects.get_or_create(
            name=name,
            defaults={'start_time': start_time, 'end_time': end_time, 'is_active': is_active},
        )
        if created:
            result.created += 1
        else:
            shift.start_time = start_time
            shift.end_time = end_time
            shift.is_active = is_active
            shift.save(update_fields=['start_time', 'end_time', 'is_active', 'updated_at'])
            result.updated += 1


@transaction.atomic
def import_shift_roster(rows, user, result):
    from apps.clinical.models import Ward
    from apps.hr.models import Shift, StaffShiftAssignment

    for i, row in enumerate(rows, start=2):
        username = row.get('nurse_username', '')
        shift_name = row.get('shift', '')
        date = _parse_date(row.get('date', ''), i, 'date', result)
        if not username or not shift_name:
            result.add_error(i, 'nurse_username and shift are required')
            continue
        if date is None:
            continue

        try:
            nurse = User.objects.get(username=username, role=Role.NURSE, is_active=True)
        except User.DoesNotExist:
            result.add_error(i, f'Nurse "{username}" not found — import staff with role nurse first')
            continue

        try:
            shift = Shift.objects.get(name__iexact=shift_name, is_active=True)
        except Shift.DoesNotExist:
            result.add_error(i, f'Shift "{shift_name}" not found — import shifts first')
            continue

        ward = None
        ward_name = row.get('ward', '')
        if ward_name:
            ward = Ward.objects.filter(name__iexact=ward_name, is_active=True).first()
            if not ward:
                result.add_error(i, f'Ward "{ward_name}" not found — import wards first or leave blank')
                continue

        assignment, created = StaffShiftAssignment.objects.update_or_create(
            staff=nurse,
            shift=shift,
            date=date,
            defaults={
                'ward': ward,
                'notes': row.get('notes', ''),
            },
        )
        if created:
            result.created += 1
        else:
            result.updated += 1


IMPORT_HANDLERS = {
    'patients': import_patients,
    'staff': import_staff,
    'drugs': import_drugs,
    'lab_tests': import_lab_tests,
    'wards': import_wards,
    'shifts': import_shifts,
    'shift_roster': import_shift_roster,
}


def run_import(import_type, uploaded_file, user):
    result = ImportResult()
    rows = parse_csv_file(uploaded_file)
    validate_headers(rows, import_type)
    handler = IMPORT_HANDLERS[import_type]
    handler(rows, user, result)
    return result
