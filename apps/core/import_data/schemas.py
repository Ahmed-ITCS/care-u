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
        'description': 'Add laboratory tests to the catalog. Category must already exist.',
        'icon': 'flask',
        'roles': ('admin', 'lab_tech'),
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
    'unit_price': {'unit_price', 'unit price', 'price'},
    'reorder_level': {'reorder_level', 'reorder level', 'min_stock'},
    'policy_number': {'policy_number', 'policy number', 'policy_no'},
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
        _col('cnic', 'CNIC', True, '35201-1234567-1', 'Format: 12345-1234567-1'),
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
        _col('category', 'Category', True, 'Blood Tests', 'Must match an existing category'),
        _col('price', 'Price', True, '800', 'PKR'),
        _col('sample_type', 'Sample Type', False, 'blood', 'blood, urine, swab, etc.'),
        _col('turnaround_hours', 'Turnaround (hrs)', False, '24', 'Expected result time'),
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
