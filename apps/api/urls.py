from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.users.views.api import AuthViewSet, MeView, UserViewSet, StaffProfileViewSet, DoctorProfileViewSet
from apps.patients.views.api import (
    PatientViewSet, InsuranceProviderViewSet, AllergyViewSet, VitalSignViewSet, PatientDocumentViewSet,
)
from apps.appointments.views.api import (
    AppointmentTypeViewSet, AppointmentViewSet, DoctorScheduleViewSet, QueueEntryViewSet,
)
from apps.clinical.views.api import (
    VisitViewSet, WardViewSet, BedViewSet, PrescriptionViewSet, AdmissionViewSet,
)
from apps.laboratory.views.api import TestCatalogViewSet, LabTestRequestViewSet
from apps.pharmacy.views.api import DrugViewSet, DispenseViewSet, PurchaseOrderViewSet, SupplierViewSet
from apps.billing.views.api import InvoiceViewSet, PaymentViewSet, ServiceCatalogViewSet
from apps.hr.views.api import (
    AttendanceViewSet, LeaveRequestViewSet, PayrollRunViewSet, ShiftViewSet,
)
from apps.notifications.views.api import NotificationViewSet
from apps.core.views.api import DepartmentViewSet, DashboardViewSet

router = DefaultRouter()
router.register('auth', AuthViewSet, basename='auth')
router.register('users', UserViewSet, basename='users')
router.register('staff-profiles', StaffProfileViewSet, basename='staff-profiles')
router.register('doctors', DoctorProfileViewSet, basename='doctors')
router.register('departments', DepartmentViewSet, basename='departments')
router.register('dashboard', DashboardViewSet, basename='dashboard')
router.register('patients', PatientViewSet, basename='patients')
router.register('insurance-providers', InsuranceProviderViewSet, basename='insurance-providers')
router.register('allergies', AllergyViewSet, basename='allergies')
router.register('vitals', VitalSignViewSet, basename='vitals')
router.register('patient-documents', PatientDocumentViewSet, basename='patient-documents')
router.register('appointment-types', AppointmentTypeViewSet, basename='appointment-types')
router.register('appointments', AppointmentViewSet, basename='appointments')
router.register('doctor-schedules', DoctorScheduleViewSet, basename='doctor-schedules')
router.register('queue', QueueEntryViewSet, basename='queue')
router.register('visits', VisitViewSet, basename='visits')
router.register('wards', WardViewSet, basename='wards')
router.register('beds', BedViewSet, basename='beds')
router.register('prescriptions', PrescriptionViewSet, basename='prescriptions')
router.register('admissions', AdmissionViewSet, basename='admissions')
router.register('lab-tests', TestCatalogViewSet, basename='lab-tests')
router.register('lab-requests', LabTestRequestViewSet, basename='lab-requests')
router.register('drugs', DrugViewSet, basename='drugs')
router.register('dispenses', DispenseViewSet, basename='dispenses')
router.register('purchase-orders', PurchaseOrderViewSet, basename='purchase-orders')
router.register('suppliers', SupplierViewSet, basename='suppliers')
router.register('services', ServiceCatalogViewSet, basename='services')
router.register('invoices', InvoiceViewSet, basename='invoices')
router.register('payments', PaymentViewSet, basename='payments')
router.register('shifts', ShiftViewSet, basename='shifts')
router.register('attendance', AttendanceViewSet, basename='attendance')
router.register('leave-requests', LeaveRequestViewSet, basename='leave-requests')
router.register('payroll', PayrollRunViewSet, basename='payroll')
router.register('notifications', NotificationViewSet, basename='notifications')

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
    path('', include(router.urls)),
]
