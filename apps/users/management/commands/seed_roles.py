from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from apps.users.models import Role, StaffProfile, DoctorProfile
from apps.core.models import Department

User = get_user_model()

DEMO_USERS = [
    ('admin', 'admin123', Role.ADMIN, 'Admin', 'User', 'admin@gph.com.pk'),
    ('doctor1', 'doctor123', Role.DOCTOR, 'Ahmed', 'Khan', 'doctor@gph.com.pk'),
    ('nurse1', 'nurse123', Role.NURSE, 'Sara', 'Ali', 'nurse@gph.com.pk'),
    ('reception1', 'reception123', Role.RECEPTIONIST, 'Fatima', 'Hassan', 'reception@gph.com.pk'),
    ('accountant1', 'accountant123', Role.ACCOUNTANT, 'Usman', 'Malik', 'accountant@gph.com.pk'),
    ('pharmacist1', 'pharmacist123', Role.PHARMACIST, 'Ayesha', 'Raza', 'pharmacist@gph.com.pk'),
    ('labtech1', 'labtech123', Role.LAB_TECH, 'Bilal', 'Ahmed', 'labtech@gph.com.pk'),
    ('patient1', 'patient123', Role.PATIENT, 'Ali', 'Hussain', 'patient@gph.com.pk'),
]


class Command(BaseCommand):
    help = 'Seed roles, groups, and demo users'

    def handle(self, *args, **options):
        for role_value, role_label in Role.choices:
            group, created = Group.objects.get_or_create(name=role_label)
            if created:
                self.stdout.write(f'Created group: {role_label}')

        departments = [
            ('General Medicine', 'GM'),
            ('Surgery', 'SUR'),
            ('Pediatrics', 'PED'),
            ('Gynecology', 'GYN'),
            ('Radiology', 'RAD'),
            ('Pathology', 'PATH'),
        ]
        for name, code in departments:
            Department.objects.get_or_create(code=code, defaults={'name': name})

        for username, password, role, first, last, email in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first,
                    'last_name': last,
                    'role': role,
                    'is_verified': True,
                },
            )
            if created:
                user.set_password(password)
                user.is_staff = role == Role.ADMIN
                user.is_superuser = role == Role.ADMIN
                user.save()
                self.stdout.write(f'Created user: {username} / {password}')

                if role in (Role.DOCTOR, Role.NURSE, Role.RECEPTIONIST, Role.ACCOUNTANT, Role.PHARMACIST, Role.LAB_TECH):
                    dept = Department.objects.first()
                    StaffProfile.objects.get_or_create(
                        user=user,
                        defaults={'department': dept, 'cnic': '12345-1234567-1'},
                    )

                if role == Role.DOCTOR:
                    DoctorProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'specialty': 'General Medicine',
                            'license_number': f'PMDC-{username.upper()}',
                            'consultation_fee': 2000,
                            'commission_rate': 10,
                        },
                    )

        self.stdout.write(self.style.SUCCESS('Roles and demo users seeded successfully'))
