from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from apps.hr.models import PayrollRun, PayrollItem, DoctorCommission
from apps.users.models import User, Role


DEFAULT_SALARIES = {
    Role.DOCTOR: Decimal('150000'),
    Role.NURSE: Decimal('60000'),
    Role.RECEPTIONIST: Decimal('45000'),
    Role.ACCOUNTANT: Decimal('70000'),
    Role.PHARMACIST: Decimal('65000'),
    Role.LAB_TECH: Decimal('55000'),
}


@transaction.atomic
def process_payroll(payroll_run, user):
    staff_users = User.objects.exclude(role=Role.PATIENT).filter(is_active=True)
    total = Decimal('0')

    for staff in staff_users:
        basic = DEFAULT_SALARIES.get(staff.role, Decimal('40000'))
        commission = Decimal('0')

        if staff.role == Role.DOCTOR:
            unpaid = DoctorCommission.objects.filter(doctor=staff, is_paid=False)
            commission = sum(c.commission_amount for c in unpaid)

        attendance_days = staff.attendance_records.filter(
            date__month=payroll_run.month,
            date__year=payroll_run.year,
            status='present',
        ).count()
        deductions = Decimal('0') if attendance_days >= 20 else Decimal('5000')

        item = PayrollItem.objects.create(
            payroll_run=payroll_run,
            staff=staff,
            basic_salary=basic,
            commission=commission,
            deductions=deductions,
            net_salary=basic + commission - deductions,
        )
        total += item.net_salary

        if staff.role == Role.DOCTOR:
            DoctorCommission.objects.filter(doctor=staff, is_paid=False).update(
                is_paid=True, payroll_item=item
            )

    payroll_run.status = 'processed'
    payroll_run.total_amount = total
    payroll_run.processed_by = user
    payroll_run.processed_at = timezone.now()
    payroll_run.save()
    return payroll_run


def approve_leave(leave, user, notes=''):
    leave.status = 'approved'
    leave.approved_by = user
    leave.approval_notes = notes
    leave.save(update_fields=['status', 'approved_by', 'approval_notes', 'updated_at'])
    return leave


def reject_leave(leave, user, notes=''):
    leave.status = 'rejected'
    leave.approved_by = user
    leave.approval_notes = notes
    leave.save(update_fields=['status', 'approved_by', 'approval_notes', 'updated_at'])
    return leave
