import re

CNIC_PATTERN = re.compile(r'^\d{5}-\d{7}-\d$')


def format_cnic(value):
    """Normalize CNIC input to XXXXX-XXXXXXX-X (13 digits)."""
    if not value:
        return value
    digits = re.sub(r'\D', '', str(value).strip())
    if len(digits) != 13:
        return str(value).strip()
    return f'{digits[:5]}-{digits[5:12]}-{digits[12]}'


def is_valid_cnic(value):
    return bool(value and CNIC_PATTERN.match(value))
