"""CSV import schemas — column definitions, aliases, and sample rows."""

IMPORT_TYPES = {
    'patients': {
        'label': 'Patients',
        'description': 'Bulk register patient records. CNIC must be unique per hospital.',
        'icon': 'users',
        'roles': ('admin', 'receptionist'),
    },
    'staff': {
        'label': 'Staff',
        'description': 'Create staff accounts for your hospital. Each hospital manages its own staff separately.',
        'icon': 'user-cog',
        'roles': ('admin',),
    },
    'drugs': {
        'label': 'Pharmacy Drugs',
        'description': 'Add drugs to the pharmacy inventory catalog.',
        'icon': 'pill',
        'roles': ('admin', 'pharmacist'),
    },
    'lab_tests': {
        'label': 'Lab Tests',
        'description': 'Add laboratory tests to the catalog. Categories are created if missing.',
        'icon': 'flask',
        'roles': ('admin', 'lab_tech'),
    },
    'wards': {
        'label': 'Wards',
        'description': 'Bulk create hospital wards used for admissions and shift roster.',
        'icon': 'bed',
        'roles': ('admin',),
    },
    'shifts': {
        'label': 'Shifts',
        'description': 'Define work shifts (morning, evening, night) for the shift roster.',
        'icon': 'clock',
        'roles': ('admin',),
    },
    'shift_roster': {
        'label': 'Shift Roster',
        'description': 'Assign nurses to shifts and wards by date. Import shifts and nurses first.',
        'icon': 'briefcase',
        'roles': ('admin',),
    },
}

COLUMN_ALIASES = {
    'first_name': {'first_name', 'firstname', 'first name', 'given_name'},
    'last_name': {'last_name', 'lastname', 'last name', 'surname', 'family_name'},
    'date_of_birth': {'date_of_birth', 'dob', 'birth_date', 'birthdate', 'date of birth'},
    'blood_group': {'blood_group', 'blood group', 'blood_type', 'blood type'},
    'license_number': {'license_number', 'license', 'pmdc', 'license no'},
    'consultation_fee': {'consultation_fee', 'consultation fee', 'fee'},
    'generic_name': {'generic_name', 'generic name', 'generic'},
    'brand_name': {'brand_name', 'brand name', 'brand'},
    'unit_price': {'unit_price', 'unit price'},
    'reorder_level': {'reorder_level', 'reorder level', 'min_stock'},
    'policy_number': {'policy_number', 'policy number', 'policy_no'},
    'ward_type': {'ward_type', 'ward type', 'type'},
    'start_time': {'start_time', 'start time', 'start'},
    'end_time': {'end_time', 'end time', 'end'},
    'nurse_username': {'nurse_username', 'nurse username', 'nurse', 'username', 'staff_username'},
}


def _col(key, label, required=False, example='', hint=''):
    return {
        'key': key,
        'label': label,
        'required': required,
        'example': example,
        'hint': hint,
    }


IMPORT_COLUMNS = {
    'patients': [
        _col('cnic', 'CNIC', True, '35201-1234567-1', '12345-1234567-1 or 13 digits without dashes'),
        _col('first_name', 'First Name', True, 'Ahmed', ''),
        _col('last_name', 'Last Name', True, 'Hassan', ''),
        _col('phone', 'Phone', True, '03001234567', 'Mobile number'),
        _col('date_of_birth', 'Date of Birth', False, '1990-05-15', 'YYYY-MM-DD'),
        _col('gender', 'Gender', False, 'M', 'M, F, or O'),
        _col('blood_group', 'Blood Group', False, 'B+', 'A+, A-, B+, B-, AB+, AB-, O+, O-'),
        _col('email', 'Email', False, 'ahmed@email.com', ''),
        _col('address', 'Address', False, 'House 12, F-8', ''),
        _col('city', 'City', False, 'Islamabad', 'Defaults to Islamabad if blank'),
        _col('notes', 'Notes', False, 'Diabetic', 'Optional clinical notes'),
    ],
    'staff': [
        _col('username', 'Username', True, 'doctor2', 'Login username, must be unique'),
        _col('first_name', 'First Name', True, 'Sara', ''),
        _col('last_name', 'Last Name', True, 'Khan', ''),
        _col('email', 'Email', True, 'sara@hospital.com', ''),
        _col('role', 'Role', True, 'doctor', 'doctor, nurse, receptionist, accountant, pharmacist, lab_tech'),
        _col('phone', 'Phone', False, '03009876543', ''),
        _col('cnic', 'CNIC', False, '35201-1234567-1', 'Optional staff CNIC'),
        _col('password', 'Password', False, 'changeme123', 'Defaults to changeme123 if blank'),
        _col('specialty', 'Specialty', False, 'Cardiology', 'Required for doctors'),
        _col('license_number', 'License #', False, 'PMDC-12345', 'Required for doctors'),
        _col('consultation_fee', 'Consultation Fee', False, '2500', 'PKR amount for doctors'),
    ],
    'drugs': [
        _col('generic_name', 'Generic Name', True, 'Paracetamol', ''),
        _col('brand_name', 'Brand Name', False, 'Panadol', ''),
        _col('strength', 'Strength', False, '500mg', ''),
        _col('form', 'Form', False, 'Tablet', 'Tablet, Syrup, Injection, etc.'),
        _col('unit_price', 'Unit Price', False, '5', 'PKR per unit'),
        _col('category', 'Category', False, 'General', 'Created if missing'),
        _col('reorder_level', 'Reorder Level', False, '10', 'Minimum stock alert level'),
    ],
    'lab_tests': [
        _col('code', 'Test Code', True, 'CBC', 'Short unique code'),
        _col('name', 'Test Name', True, 'Complete Blood Count', ''),
        _col('category', 'Category', True, 'Blood Tests', 'Created if missing'),
        _col('price', 'Price', True, '800', 'PKR'),
        _col('sample_type', 'Sample Type', False, 'blood', 'blood, urine, swab, etc.'),
        _col('turnaround_hours', 'Turnaround (hrs)', False, '24', 'Expected result time'),
    ],
    'wards': [
        _col('name', 'Ward Name', True, 'General Ward', 'Unique per hospital'),
        _col('ward_type', 'Ward Type', False, 'general', 'general, icu, pediatric, maternity, private, emergency'),
        _col('floor', 'Floor', False, '2', 'Optional floor label'),
        _col('capacity', 'Capacity', False, '20', 'Bed capacity (informational)'),
    ],
    'shifts': [
        _col('name', 'Shift Name', True, 'Morning', 'e.g. Morning, Evening, Night'),
        _col('start_time', 'Start Time', True, '08:00', 'HH:MM (24-hour)'),
        _col('end_time', 'End Time', True, '16:00', 'HH:MM (24-hour)'),
        _col('is_active', 'Active', False, 'yes', 'yes/no — defaults to yes'),
    ],
    'shift_roster': [
        _col('nurse_username', 'Nurse Username', True, 'nurse1', 'Must match an existing nurse login'),
        _col('shift', 'Shift Name', True, 'Morning', 'Must match an imported shift name'),
        _col('date', 'Date', True, '2026-06-28', 'YYYY-MM-DD'),
        _col('ward', 'Ward', False, 'General Ward', 'Optional — must match an existing ward'),
        _col('notes', 'Notes', False, 'ICU cover', 'Optional'),
    ],
}

SAMPLE_ROWS = {
    'patients': [
        {
            'cnic': '35201-1234567-1', 'first_name': 'Ahmed', 'last_name': 'Hassan',
            'phone': '03001234567', 'date_of_birth': '1990-05-15', 'gender': 'M',
            'blood_group': 'B+', 'email': 'ahmed@email.com', 'address': 'F-8 Markaz',
            'city': 'Islamabad', 'notes': '',
        },
        {
            'cnic': '35201-2345678-1', 'first_name': 'Fatima', 'last_name': 'Khan',
            'phone': '03009876543', 'date_of_birth': '1985-11-20', 'gender': 'F',
            'blood_group': 'O+', 'email': '', 'address': '', 'city': 'Rawalpindi', 'notes': '',
        },
    ],
    'staff': [
        {
            'username': 'doctor2', 'first_name': 'Sara', 'last_name': 'Khan',
            'email': 'sara@hospital.com', 'role': 'doctor', 'phone': '03001112222',
            'password': 'changeme123', 'specialty': 'Cardiology',
            'license_number': 'PMDC-98765', 'consultation_fee': '3000',
        },
    ],
    'drugs': [
        {
            'generic_name': 'Paracetamol', 'brand_name': 'Panadol', 'strength': '500mg',
            'form': 'Tablet', 'unit_price': '5', 'category': 'General', 'reorder_level': '50',
        },
        {
            'generic_name': 'Amoxicillin', 'brand_name': 'Augmentin', 'strength': '625mg',
            'form': 'Tablet', 'unit_price': '25', 'category': 'Antibiotics', 'reorder_level': '20',
        },
    ],
    'lab_tests': [
        {
            'code': 'CBC', 'name': 'Complete Blood Count', 'category': 'Blood Tests',
            'price': '800', 'sample_type': 'blood', 'turnaround_hours': '24',
        },
        {
            'code': 'LFT', 'name': 'Liver Function Test', 'category': 'Blood Tests',
            'price': '1200', 'sample_type': 'blood', 'turnaround_hours': '48',
        },
    ],
    'wards': [
        {'name': 'General Ward', 'ward_type': 'general', 'floor': '2', 'capacity': '24'},
        {'name': 'ICU', 'ward_type': 'icu', 'floor': '3', 'capacity': '8'},
    ],
    'shifts': [
        {'name': 'Morning', 'start_time': '08:00', 'end_time': '16:00', 'is_active': 'yes'},
        {'name': 'Evening', 'start_time': '16:00', 'end_time': '00:00', 'is_active': 'yes'},
        {'name': 'Night', 'start_time': '00:00', 'end_time': '08:00', 'is_active': 'yes'},
    ],
    'shift_roster': [
        {
            'nurse_username': 'nurse1', 'shift': 'Morning', 'date': '2026-06-28',
            'ward': 'General Ward', 'notes': '',
        },
        {
            'nurse_username': 'nurse2', 'shift': 'Evening', 'date': '2026-06-28',
            'ward': 'ICU', 'notes': 'Night cover',
        },
    ],
}


def normalize_header(header):
    key = header.strip().lower().replace(' ', '_').replace('-', '_')
    for canonical, aliases in COLUMN_ALIASES.items():
        if key in aliases or key == canonical:
            return canonical
    return key


def get_columns(import_type):
    return IMPORT_COLUMNS.get(import_type, [])


def get_required_keys(import_type):
    return [c['key'] for c in get_columns(import_type) if c['required']]
