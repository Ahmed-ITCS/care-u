import pytest

from apps.laboratory.models import TestCatalog, TestCategory
from apps.users.models import Role, User


@pytest.fixture
def lab_tech_user(db):
    return User.objects.create_user(
        username='testlabtech', password='testpass123',
        role=Role.LAB_TECH, email='labtech@test.com',
    )


@pytest.mark.django_db
class TestLabCatalog:
    def test_lab_tech_can_view_catalog(self, client, tenant_prefix, lab_tech_user):
        client.force_login(lab_tech_user)
        response = client.get(f'{tenant_prefix}/laboratory/tests/')
        assert response.status_code == 200

    def test_lab_tech_can_add_test(self, client, tenant_prefix, lab_tech_user):
        category = TestCategory.objects.create(name='Blood Tests')
        client.force_login(lab_tech_user)
        url = f'{tenant_prefix}/laboratory/tests/add/'
        response = client.post(url, {
            'category': category.pk,
            'code': 'TSH',
            'name': 'Thyroid Stimulating Hormone',
            'description': '',
            'sample_type': 'blood',
            'price': '1500',
            'turnaround_hours': '24',
            'is_active': 'on',
        })
        assert response.status_code == 302
        test = TestCatalog.objects.get(code='TSH')
        assert test.name == 'Thyroid Stimulating Hormone'
        assert test.category_id == category.pk

    def test_lab_tech_can_add_test_with_new_category(self, client, tenant_prefix, lab_tech_user):
        client.force_login(lab_tech_user)
        url = f'{tenant_prefix}/laboratory/tests/add/'
        response = client.post(url, {
            'new_category': 'Microbiology',
            'code': 'CULT',
            'name': 'Culture & Sensitivity',
            'description': '',
            'sample_type': 'swab',
            'price': '2500',
            'turnaround_hours': '72',
            'is_active': 'on',
        })
        assert response.status_code == 302
        assert TestCategory.objects.filter(name='Microbiology').exists()
        assert TestCatalog.objects.filter(code='CULT').exists()

    def test_doctor_cannot_access_catalog(self, client, tenant_prefix, doctor_user):
        client.force_login(doctor_user)
        response = client.get(f'{tenant_prefix}/laboratory/tests/')
        assert response.status_code == 302
