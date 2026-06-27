import pytest
from django.utils import timezone

from apps.clinical.models import Ward
from apps.hr.models import Shift, StaffShiftAssignment
from apps.users.models import Role, User


@pytest.fixture
def nurse_user(db):
    return User.objects.create_user(
        username='testnurse',
        password='testpass123',
        role=Role.NURSE,
        email='nurse@test.com',
        first_name='Sara',
        last_name='Nurse',
    )


@pytest.fixture
def morning_shift(db):
    from datetime import time
    return Shift.objects.create(name='Morning', start_time=time(8, 0), end_time=time(16, 0))


@pytest.fixture
def general_ward(db):
    return Ward.objects.create(name='General Ward', ward_type='general', capacity=20)


@pytest.mark.django_db
class TestShiftRoster:
    def test_admin_can_view_roster(self, client, tenant_prefix, admin_user, morning_shift):
        client.force_login(admin_user)
        today = timezone.localdate().isoformat()
        response = client.get(f'{tenant_prefix}/hr/roster/?date={today}')
        assert response.status_code == 200
        assert 'Shift Roster' in response.content.decode()

    def test_admin_can_assign_nurse(
        self, client, tenant_prefix, admin_user, nurse_user, morning_shift, general_ward,
    ):
        client.force_login(admin_user)
        today = timezone.localdate()
        response = client.post(f'{tenant_prefix}/hr/roster/new/', {
            'staff': nurse_user.pk,
            'shift': morning_shift.pk,
            'ward': general_ward.pk,
            'date': today.isoformat(),
            'notes': 'Cover ICU overflow',
        })
        assert response.status_code == 302
        assignment = StaffShiftAssignment.objects.get(staff=nurse_user, date=today)
        assert assignment.ward_id == general_ward.pk
        assert assignment.notes == 'Cover ICU overflow'

    def test_nurse_can_view_my_roster(
        self, client, tenant_prefix, nurse_user, morning_shift, general_ward,
    ):
        StaffShiftAssignment.objects.create(
            staff=nurse_user,
            shift=morning_shift,
            ward=general_ward,
            date=timezone.localdate(),
        )
        client.force_login(nurse_user)
        response = client.get(f'{tenant_prefix}/hr/my-roster/')
        assert response.status_code == 200
        assert 'General Ward' in response.content.decode()

    def test_non_nurse_cannot_view_my_roster(self, client, tenant_prefix, receptionist_user):
        client.force_login(receptionist_user)
        response = client.get(f'{tenant_prefix}/hr/my-roster/')
        assert response.status_code == 302
