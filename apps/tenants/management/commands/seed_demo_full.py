"""
Populate the demo tenant (gph-islamabad) with realistic sample data spanning the
last 30 days so every major module page shows content during a sales demo.

Usage:
    python manage.py seed_demo_full
    python manage.py seed_demo_full --subdomain gph-islamabad

Safe to re-run: every module uses existence-guards / get_or_create so duplicates
are avoided. Complements (does not duplicate) seed_demo_metrics.
"""
from datetime import date, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tenants.models import Hospital
from apps.tenants.sqlite_compat import tenant_schema_context
from apps.users.models import Role


class Command(BaseCommand):
    help = 'Seed comprehensive 30-day demo data for all ERP modules.'

    def add_arguments(self, parser):
        parser.add_argument('--subdomain', default='gph-islamabad')

    def handle(self, *args, **options):
        subdomain = options['subdomain'].lower().strip()
        hospital = Hospital.objects.filter(subdomain=subdomain).first()
        if not hospital:
            self.stderr.write(self.style.ERROR(f'Hospital "{subdomain}" not found.'))
            raise SystemExit(1)

        self.hospital = hospital
        with tenant_schema_context(hospital.schema_name):
            self.today = timezone.now().date()
            self.now = timezone.now()
            self.patients = []
            self.appointments = []
            self.opd_visits = []
            self._load_staff()

            modules = [
                ('patients', self._seed_patients),
                ('appointments', self._seed_appointments),
                ('clinical', self._seed_clinical),
                ('laboratory', self._seed_laboratory),
                ('pharmacy', self._seed_pharmacy),
                ('billing', self._seed_billing),
                ('hr', self._seed_hr),
            ]
            for name, fn in modules:
                try:
                    fn()
                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(self.style.ERROR(f'  [{name}] FAILED: {exc}'))

        self._print_summary()

    def _backdate(self, obj, dt):
        if hasattr(obj, 'created_at'):
            obj.created_at = dt
            obj.save(update_fields=['created_at'])

    def _load_staff(self):
        from apps.users.models import User

        self.doctor = User.objects.filter(role=Role.DOCTOR).first()
        self.doctor2 = User.objects.filter(username='doctor2').first()
        self.receptionist = User.objects.filter(role=Role.RECEPTIONIST).first()
        self.pharmacist = User.objects.filter(role=Role.PHARMACIST).first()
        self.lab_tech = User.objects.filter(role=Role.LAB_TECH).first()
        self.nurse = User.objects.filter(role=Role.NURSE).first()
        self.admin = User.objects.filter(role=Role.ADMIN).first()
        self.booked_by = self.receptionist or self.admin

        from apps.users.models import User
        if not User.objects.filter(username='doctor2').exists():
            d2 = User.objects.create_user(
                username='doctor2', password='doctor123', role=Role.DOCTOR,
                first_name='Sara', last_name='Malik', email='doctor2@demo.pk',
                phone='0302-0000002', is_verified=True,
            )
            from apps.users.models import DoctorProfile
            DoctorProfile.objects.create(
                user=d2, specialty='Pediatrics', license_number='PMDC-002',
                commission_rate=Decimal('10.00'), consultation_fee=Decimal('2500.00'),
            )
        self.doctor2 = User.objects.filter(username='doctor2').first()

    def _dt(self, days_ago):
        return self.now - timedelta(days=days_ago)

    def _seed_patients(self):
        from apps.patients.models import (
            Allergy, MedicalHistory, Patient, PatientInsurance, VitalSign,
            InsuranceProvider,
        )

        if Patient.objects.filter(cnic__startswith='35202-').exists():
            self.stdout.write('  Patients already seeded — skipping.')
            self.patients = list(Patient.objects.filter(cnic__startswith='35202-'))
            return

        male_first = ['Bilal', 'Hassan', 'Imran', 'Kashif', 'Omer', 'Rehan', 'Tariq', 'Waqas', 'Faisal', 'Usman']
        female_first = ['Ayesha', 'Madiha', 'Nabila', 'Rabia', 'Sadia', 'Zainab', 'Amina', 'Sana', 'Hira', 'Sobia']
        last = ['Ahmed', 'Bhatti', 'Chaudhry', 'Farooq', 'Gill', 'Hussain', 'Javed', 'Khan', 'Malik', 'Sheikh']
        cities = ['Islamabad', 'Rawalpindi', 'Lahore', 'Karachi', 'Peshawar', 'Faisalabad']
        blood = ['A+', 'B+', 'O+', 'AB+', 'A-', 'B-', 'O-', 'AB-']
        allergens = [('Penicillin', 'Rash', 'severe'), ('Dust', 'Sneezing', 'mild'),
                     ('Pollen', 'Itchy eyes', 'moderate'), ('NSAIDs', 'Swelling', 'severe'),
                     ('Shellfish', 'Hives', 'moderate')]
        conditions = ['Hypertension', 'Type 2 Diabetes', 'Asthma', 'Hypothyroidism',
                      'Chronic back pain', 'Migraine', 'Anemia']

        provider, _ = InsuranceProvider.objects.get_or_create(
            name='Care Health Insurance', defaults={'contact_phone': '+92-51-111222333',
                                                    'contact_email': 'claims@carehealth.pk'}
        )

        self.patients = []
        for i in range(30):
            gender = 'M' if i % 2 == 0 else 'F'
            first = (male_first + female_first)[i % (len(male_first) + len(female_first))]
            last_n = last[i % len(last)]
            year = 1955 + (i * 2) % 50
            cnic = f'35202-{2000000 + i}-{(i % 9) + 1}'
            dob = date(year, 1 + (i % 12), 1 + (i % 27))
            p, _ = Patient.objects.get_or_create(
                cnic=cnic,
                defaults={
                    'first_name': first,
                    'last_name': last_n,
                    'phone': f'0301{3000000 + i}'[:11],
                    'gender': gender,
                    'city': cities[i % len(cities)],
                    'date_of_birth': dob,
                    'blood_group': blood[i % len(blood)],
                    'registered_by': self.booked_by,
                    'address': f'House {i + 1}, Street {i % 10}, {cities[i % len(cities)]}',
                },
            )
            self.patients.append(p)

            days = (i * 3) % 30
            self._backdate(p, self._dt(days))

            if i % 3 == 0:
                Allergy.objects.get_or_create(
                    patient=p, allergen=allergens[(i // 3) % len(allergens)][0],
                    defaults={
                        'reaction': allergens[(i // 3) % len(allergens)][1],
                        'severity': allergens[(i // 3) % len(allergens)][2],
                        'noted_by': self.doctor,
                    },
                )

            if i % 2 == 0:
                VitalSign.objects.get_or_create(
                    patient=p, recorded_by=self.nurse,
                    defaults={
                        'temperature': Decimal(str(36.5 + (i % 3) * 0.4)),
                        'blood_pressure_systolic': 110 + (i % 40),
                        'blood_pressure_diastolic': 70 + (i % 20),
                        'pulse': 70 + (i % 30),
                        'respiratory_rate': 16 + (i % 6),
                        'oxygen_saturation': Decimal(str(96 + (i % 4))),
                        'weight': Decimal(str(55 + (i % 40))),
                        'height': Decimal(str(150 + (i % 35))),
                    },
                )

            if i % 4 == 0:
                PatientInsurance.objects.get_or_create(
                    patient=p, provider=provider,
                    defaults={
                        'policy_number': f'CHI-{2024}-{1000 + i}',
                        'coverage_amount': Decimal('500000.00'),
                        'valid_from': self.today - timedelta(days=120),
                        'valid_until': self.today + timedelta(days=245),
                        'is_primary': True,
                    },
                )

            if i % 2 == 1:
                MedicalHistory.objects.get_or_create(
                    patient=p, title=conditions[(i // 2) % len(conditions)],
                    defaults={
                        'description': f'Diagnosed and managed for {conditions[(i // 2) % len(conditions)].lower()}.',
                        'recorded_date': self.today - timedelta(days=(i * 5) % 400),
                        'recorded_by': self.doctor,
                    },
                )

        self.stdout.write(f'  Patients: {len(self.patients)} (new demo cohort)')

    def _seed_appointments(self):
        from apps.appointments.models import Appointment, AppointmentType, QueueEntry

        if Appointment.objects.filter(reason__startswith='DEMO30-').exists():
            self.stdout.write('  Appointments already seeded — skipping.')
            self.appointments = list(Appointment.objects.filter(reason__startswith='DEMO30-'))
            return

        opd_type = AppointmentType.objects.filter(code='OPD').first()
        fu_type = AppointmentType.objects.filter(code='Follow-up').first()
        doctors = [d for d in [self.doctor, self.doctor2] if d]
        statuses = ['scheduled', 'confirmed', 'completed', 'cancelled']
        slots = [time(9, 0), time(9, 30), time(10, 0), time(10, 30),
                 time(11, 0), time(11, 30), time(14, 0), time(14, 30),
                 time(15, 0), time(15, 30)]

        self.appointments = []
        token_counter = [0]
        appt_idx = 0
        for day in range(30):
            d = self.today - timedelta(days=day)
            for s in range(3 if day > 0 else 8):
                if appt_idx >= len(self.patients):
                    break
                patient = self.patients[appt_idx % len(self.patients)]
                doctor = doctors[appt_idx % len(doctors)]
                slot = slots[(appt_idx + s) % len(slots)]
                if day == 0:
                    status = 'scheduled'
                else:
                    status = statuses[appt_idx % len(statuses)]
                appt_type = fu_type if (appt_idx % 5 == 0 and fu_type) else opd_type
                appt, created = Appointment.objects.get_or_create(
                    patient=patient, doctor=doctor, scheduled_date=d, scheduled_time=slot,
                    defaults={
                        'appointment_type': appt_type,
                        'status': status,
                        'source': 'walk_in' if appt_idx % 2 == 0 else 'phone',
                        'booked_by': self.booked_by,
                        'reason': f'DEMO30-{appt_idx}',
                    },
                )
                if created:
                    self.appointments.append(appt)
                appt_idx += 1

        self.stdout.write(f'  Appointments (30d): {len(self.appointments)} created')

        today_appts = [a for a in self.appointments if a.scheduled_date == self.today]
        waiting = 0
        for a in today_appts[:6]:
            if QueueEntry.objects.filter(appointment=a).exists():
                continue
            token_counter[0] += 1
            qstatus = 'waiting' if waiting < 3 else ('in_consultation' if waiting < 5 else 'completed')
            called = self._dt(0) - timedelta(minutes=10) if qstatus != 'waiting' else None
            QueueEntry.objects.create(
                appointment=a, token_number=token_counter[0],
                priority=1 if a.appointment_type_id and a.reason and appt_idx % 7 == 0 else 0,
                status=qstatus, called_at=called,
            )
            waiting += 1
        self.stdout.write(f'  Queue entries (today): {QueueEntry.objects.filter(created_at__date=self.today).count()}')

    def _seed_clinical(self):
        from apps.clinical.models import (
            Admission, Bed, Diagnosis, NursingNote, OPDVisit, Prescription,
            PrescriptionItem, Visit, Ward,
        )
        from apps.patients.models import Patient

        completed = [a for a in getattr(self, 'appointments', [])
                     if a.status == 'completed']
        if not completed and self.patients:
            completed = self.appointments[:10]

        visits_created = 0
        self.opd_visits = []
        chief = ['Fever and cough for 4 days', 'Severe headache since morning',
                 'Chest pain on exertion', 'Abdominal pain and vomiting',
                 'Shortness of breath', 'Joint pain and swelling',
                 'Dizziness and fatigue', 'Sore throat and runny nose']
        exams = ['Vitals stable, chest clear on auscultation.',
                 'Mild tenderness in right upper quadrant.',
                 'BP mildly elevated, no focal deficits.',
                 'Conjunctiva pale, dehydration noted.']
        diags = ['Viral upper respiratory infection', 'Acute gastritis',
                 'Essential hypertension', 'Acute bronchitis',
                 'Iron deficiency anemia', 'Acute tonsillitis']
        plans = ['Rest, hydration, antipyretics PRN.', 'PPI once daily for 2 weeks.',
                 'Lifestyle modification, recheck in 2 weeks.',
                 'Antibiotics for 5 days, follow up if no improvement.']

        for i, appt in enumerate(completed[:18]):
            visit, vcreated = Visit.objects.get_or_create(
                appointment=appt,
                defaults={
                    'patient': appt.patient, 'doctor': appt.doctor,
                    'visit_type': 'opd', 'status': 'completed',
                    'notes': 'Consultation',
                },
            )
            if vcreated:
                visits_created += 1
                self._backdate(visit, self._dt((i * 2) % 30))
            self.opd_visits.append(visit)

            OPDVisit.objects.get_or_create(
                visit=visit,
                defaults={
                    'chief_complaint': chief[i % len(chief)],
                    'examination': exams[i % len(exams)],
                    'diagnosis': diags[i % len(diags)],
                    'treatment_plan': plans[i % len(plans)],
                    'follow_up_date': self.today + timedelta(days=7),
                },
            )
            Diagnosis.objects.get_or_create(
                visit=visit, description=diags[i % len(diags)],
                defaults={'icd10_code': f'J0{i % 9 + 1}', 'is_primary': True},
            )
            rx, rxcreated = Prescription.objects.get_or_create(
                visit=visit, defaults={'doctor': appt.doctor, 'status': 'dispensed' if i % 2 == 0 else 'active'}
            )
            if rxcreated:
                drugs_list = ['Paracetamol 500mg', 'Amoxicillin 625mg', 'Omeprazole 20mg', 'Metformin 500mg']
                for j in range(1 + (i % 2)):
                    PrescriptionItem.objects.get_or_create(
                        prescription=rx,
                        drug_name=drugs_list[(i + j) % len(drugs_list)],
                        defaults={
                            'dosage': '1 tablet',
                            'frequency': 'Twice daily' if j == 0 else 'Once daily',
                            'duration': '5 days' if j == 0 else '14 days',
                            'quantity': 10 if j == 0 else 28,
                            'instructions': 'After meals',
                        },
                    )
        self.stdout.write(f'  Visits (OPD): {visits_created} | Prescriptions: {Prescription.objects.count()}')

        ward, _ = Ward.objects.get_or_create(name='General Ward A')
        beds = list(Bed.objects.filter(ward=ward))
        if not beds:
            beds = [Bed.objects.create(ward=ward, bed_number=str(n), status='vacant', daily_rate=3000)
                    for n in range(1, 6)]
        ipd_patients = [p for p in self.patients[::5]][:2]
        ipd_doctors = [d for d in [self.doctor, self.doctor2] if d]
        for i, patient in enumerate(ipd_patients):
            if Admission.objects.filter(patient=patient, is_active=True).exists():
                continue
            bed = beds[i % len(beds)]
            visit, _ = Visit.objects.get_or_create(
                patient=patient, doctor=ipd_doctors[i % len(ipd_doctors)],
                visit_type='ipd',
                defaults={'status': 'completed', 'notes': 'IPD admission'},
            )
            self._backdate(visit, self._dt(10 + i * 3))
            adm = Admission.objects.create(
                patient=patient, visit=visit, bed=bed,
                admitting_doctor=ipd_doctors[i % len(ipd_doctors)],
                reason='Requires monitoring and IV therapy',
                expected_discharge=self.today + timedelta(days=2),
                is_active=True,
            )
            NursingNote.objects.get_or_create(
                admission=adm, nurse=self.nurse,
                defaults={
                    'note': 'Patient stable, vitals monitored.',
                    'vitals_summary': 'BP 120/80, Pulse 78, Temp 37.0C',
                },
            )
        self.stdout.write(f'  IPD Admissions: {Admission.objects.count()} | Nursing notes: {NursingNote.objects.count()}')

    def _seed_laboratory(self):
        from apps.laboratory.models import (
            LabReport, LabTestRequest, LabTestRequestItem, SampleCollection,
            TestCatalog, TestResult,
        )

        if not self.patients:
            self.stdout.write('  No patients — skipping lab seed.')
            return

        if LabTestRequest.objects.filter(request_number__startswith='LAB-DEMO-').exists():
            self.stdout.write('  Lab requests already seeded — skipping.')
            return

        catalog = list(TestCatalog.objects.all())
        statuses = ['requested', 'collected', 'in_progress', 'completed']
        priorities = ['normal', 'urgent', 'stat']
        results_map = {
            'CBC': ('12.5', '10^12/L', '4.0-11.0', False),
            'LFT': ('45', 'U/L', '7-56', False),
            'RFT': ('1.1', 'mg/dL', '0.6-1.3', False),
            'URINE': ('Normal', '', 'Normal', False),
            'XRAY': ('No acute findings', '', '', False),
        }
        completed_count = 0
        for i in range(25):
            patient = self.patients[i % len(self.patients)]
            days = (i * 2) % 30
            req, created = LabTestRequest.objects.get_or_create(
                request_number=f'LAB-DEMO-{i:03d}',
                defaults={
                    'patient': patient,
                    'visit': self.opd_visits[i % len(self.opd_visits)] if self.opd_visits else None,
                    'requested_by': self.doctor,
                    'status': statuses[i % len(statuses)],
                    'priority': priorities[i % len(priorities)],
                    'clinical_notes': 'Routine investigation',
                },
            )
            if created:
                self._backdate(req, self._dt(days))
            if not req.items.exists():
                test = catalog[i % len(catalog)]
                item = LabTestRequestItem.objects.create(request=req, test=test, status=req.status)
                if req.status in ('collected', 'in_progress', 'completed'):
                    SampleCollection.objects.get_or_create(
                        request_item=item,
                        defaults={'collected_by': self.lab_tech,
                                  'sample_id': f'SMP-{i:04d}', 'collection_notes': 'Collected venously'},
                    )
                if req.status == 'completed':
                    completed_count += 1
                    val, unit, ref, abn = results_map.get(test.code, ('Normal', '', 'Normal', False))
                    if i % 6 == 0:
                        abn = True
                        val = '14.8'
                        ref = '4.0-11.0'
                    TestResult.objects.get_or_create(
                        request_item=item,
                        defaults={
                            'result_value': val, 'unit': unit, 'reference_range': ref,
                            'is_abnormal': abn, 'entered_by': self.lab_tech,
                            'verified_by': self.lab_tech,
                        },
                    )
                    LabReport.objects.get_or_create(
                        request=req, defaults={'generated_by': self.lab_tech, 'is_final': True}
                    )
        total = LabTestRequest.objects.filter(request_number__startswith='LAB-DEMO-').count()
        self.stdout.write(f'  Lab requests: {total} (completed: {completed_count}) | '
                          f'Results: {TestResult.objects.count()} | Reports: {LabReport.objects.count()}')

    def _seed_pharmacy(self):
        from apps.pharmacy.models import (
            Dispense, DispenseItem, Drug, DrugBatch, DrugCategory, PurchaseOrder,
            PurchaseOrderItem, StockMovement, Supplier,
        )
        from apps.clinical.models import Prescription

        if not self.patients:
            self.stdout.write('  No patients — skipping pharmacy seed.')
            return

        cat, _ = DrugCategory.objects.get_or_create(name='General')
        extra_drugs = [
            ('Ibuprofen', 'Brufen', '400mg', 'Tablet', 12),
            ('Cefixime', 'Cefspan', '200mg', 'Capsule', 18),
            ('Azithromycin', 'Azomax', '500mg', 'Tablet', 20),
            ('Salbutamol', 'Ventolin', '100mcg', 'Inhaler', 30),
        ]
        drugs = list(Drug.objects.all())
        for generic, brand, strength, form, price in extra_drugs:
            d, _ = Drug.objects.get_or_create(
                generic_name=generic, strength=strength,
                defaults={'category': cat, 'brand_name': brand, 'form': form,
                          'unit_price': price, 'reorder_level': 10},
            )
            drugs.append(d)

        supplier, _ = Supplier.objects.get_or_create(
            name='Demo Pharma Supplies', defaults={'phone': '+92-51-5551234',
                                                   'email': 'sales@demopharma.pk'}
        )
        if not DrugBatch.objects.filter(batch_number__startswith='DEMO-').exists():
            for idx, drug in enumerate(drugs):
                healthy = DrugBatch.objects.create(
                    drug=drug, batch_number=f'DEMO-H{idx:02d}',
                    expiry_date=self.today + timedelta(days=400),
                    quantity=80, purchase_price=drug.unit_price * Decimal('0.7'),
                    supplier=supplier,
                )
                StockMovement.objects.create(
                    drug=drug, batch=healthy, movement_type='in', quantity=80,
                    reference='Initial stock', performed_by=self.pharmacist,
                )
                low = DrugBatch.objects.create(
                    drug=drug, batch_number=f'DEMO-L{idx:02d}',
                    expiry_date=self.today + timedelta(days=200),
                    quantity=4, purchase_price=drug.unit_price * Decimal('0.7'),
                    supplier=supplier,
                )
                expiring = DrugBatch.objects.create(
                    drug=drug, batch_number=f'DEMO-E{idx:02d}',
                    expiry_date=self.today + timedelta(days=18),
                    quantity=30, purchase_price=drug.unit_price * Decimal('0.7'),
                    supplier=supplier,
                )
                expired = DrugBatch.objects.create(
                    drug=drug, batch_number=f'DEMO-X{idx:02d}',
                    expiry_date=self.today - timedelta(days=25),
                    quantity=15, purchase_price=drug.unit_price * Decimal('0.7'),
                    supplier=supplier,
                )
                StockMovement.objects.create(
                    drug=drug, batch=expired, movement_type='expired', quantity=15,
                    reference='Expired batch', performed_by=self.pharmacist,
                )
        self.stdout.write(f'  Drug batches: {DrugBatch.objects.count()} '
                          f'(low/expiring/expired demo created)')

        if not PurchaseOrder.objects.filter(po_number__startswith='PO-DEMO-').exists():
            po_statuses = ['draft', 'ordered', 'received']
            for i, status in enumerate(po_statuses):
                po = PurchaseOrder.objects.create(
                    po_number=f'PO-DEMO-{i:02d}', supplier=supplier, status=status,
                    order_date=self.today - timedelta(days=5 + i * 4),
                    expected_delivery=self.today + timedelta(days=10),
                    total_amount=Decimal('0'), created_by=self.booked_by,
                )
                total = Decimal('0')
                for j, drug in enumerate(drugs[:3]):
                    price = drug.unit_price * Decimal('0.7')
                    qty = 50 + j * 10
                    PurchaseOrderItem.objects.create(
                        purchase_order=po, drug=drug, quantity=qty, unit_price=price,
                        batch_number=f'POB-{i}{j}', expiry_date=self.today + timedelta(days=365),
                    )
                    total += price * qty
                po.total_amount = total
                po.save(update_fields=['total_amount'])
                if status == 'received':
                    for j, drug in enumerate(drugs[:3]):
                        b = DrugBatch.objects.create(
                            drug=drug, batch_number=f'POB-{i}{j}',
                            expiry_date=self.today + timedelta(days=365),
                            quantity=50 + j * 10,
                            purchase_price=drug.unit_price * Decimal('0.7'),
                            supplier=supplier,
                        )
                        StockMovement.objects.create(
                            drug=drug, batch=b, movement_type='in', quantity=50 + j * 10,
                            reference=po.po_number, performed_by=self.pharmacist,
                        )
        self.stdout.write(f'  Purchase orders: {PurchaseOrder.objects.filter(po_number__startswith="PO-DEMO-").count()}')

        rxs = list(Prescription.objects.filter(status='dispensed'))
        if not Dispense.objects.filter(notes__startswith='DEMO-').exists() and rxs:
            for i, rx in enumerate(rxs[:12]):
                days = (i * 2) % 30
                status = ['dispensed', 'pending', 'partial'][i % 3]
                dispense = Dispense.objects.create(
                    prescription=rx, patient=rx.visit.patient,
                    dispensed_by=self.pharmacist, status=status,
                    total_amount=Decimal(str(450 + (i % 5) * 120)),
                    notes=f'DEMO-{i}',
                )
                self._backdate(dispense, self._dt(days))
                items = rx.items.all()[:2]
                for it in items:
                    batch = DrugBatch.objects.filter(
                        drug__generic_name__icontains=it.drug_name.split()[0]
                    ).first()
                    if not batch:
                        batch = DrugBatch.objects.exclude(batch_number__startswith='DEMO-X').first()
                    if batch:
                        DispenseItem.objects.create(
                            dispense=dispense, prescription_item=it,
                            drug=batch.drug, batch=batch,
                            quantity=it.quantity, unit_price=batch.drug.unit_price,
                        )
                        if status == 'dispensed':
                            StockMovement.objects.create(
                                drug=batch.drug, batch=batch, movement_type='out',
                                quantity=it.quantity, reference=dispense.notes,
                                performed_by=self.pharmacist,
                            )
        self.stdout.write(f'  Dispenses: {Dispense.objects.filter(notes__startswith="DEMO-").count()} '
                          f'(Stock movements: {StockMovement.objects.count()})')

    def _seed_billing(self):
        from apps.billing.models import InsuranceClaim, Invoice, Payment
        from apps.billing.services import create_invoice_from_visit, record_payment
        from apps.patients.models import PatientInsurance

        visits = self.opd_visits if getattr(self, 'opd_visits', None) else []
        paid = partial = pending = 0
        for i, visit in enumerate(visits[:18]):
            if Invoice.objects.filter(visit=visit).exists():
                continue
            invoice = create_invoice_from_visit(visit.id, self.booked_by)
            self._backdate(invoice, self._dt((i * 2) % 30))
            mode = i % 3
            if mode == 0:
                record_payment(invoice, invoice.total_amount, 'cash', self.booked_by)
                self._backdate(invoice.payments.first(), self._dt((i * 2) % 30))
                paid += 1
            elif mode == 1:
                record_payment(invoice, invoice.total_amount / 2, 'card', self.booked_by)
                self._backdate(invoice.payments.first(), self._dt((i * 2) % 30))
                partial += 1
            else:
                invoice.due_date = self.today - timedelta(days=10 + (i % 20))
                invoice.status = 'pending'
                invoice.save(update_fields=['due_date', 'status'])
                pending += 1

        for inv in Invoice.objects.filter(status='paid').order_by('?')[:6]:
            p = inv.payments.first()
            if p:
                self._backdate(p, self._dt((hash(str(inv.id)) % 30)))

        insured_patient_ids = PatientInsurance.objects.values_list('patient_id', flat=True)
        claim_inv = Invoice.objects.filter(patient_id__in=insured_patient_ids).first()
        if claim_inv and not InsuranceClaim.objects.filter(invoice=claim_inv).exists():
            policy = PatientInsurance.objects.filter(patient=claim_inv.patient).first()
            InsuranceClaim.objects.get_or_create(
                invoice=claim_inv, policy=policy,
                defaults={
                    'claim_number': f'CLM-{claim_inv.invoice_number}',
                    'claimed_amount': claim_inv.total_amount,
                    'status': 'submitted',
                },
            )

        self.stdout.write(f'  Invoices: paid={paid} partial={partial} pending={pending} | '
                          f'total={Invoice.objects.count()} | Payments: {Payment.objects.count()} | '
                          f'Claims: {InsuranceClaim.objects.count()}')

    def _seed_hr(self):
        from apps.hr.models import (
            Attendance, DoctorCommission, LeaveRequest, PayrollItem, PayrollRun,
            Shift, StaffShiftAssignment,
        )
        from apps.clinical.models import Ward
        from apps.billing.models import Invoice

        shift, _ = Shift.objects.get_or_create(
            name='Day Shift (Demo)', defaults={'start_time': time(8, 0), 'end_time': time(20, 0)}
        )
        staff = [s for s in [self.doctor, self.doctor2, self.nurse, self.receptionist,
                             self.pharmacist, self.lab_tech] if s]
        assignments = 0
        for day in range(14):
            d = self.today - timedelta(days=day)
            for st in staff:
                _, created = StaffShiftAssignment.objects.get_or_create(
                    staff=st, date=d, shift=shift,
                    defaults={'ward': Ward.objects.first(), 'notes': 'Scheduled shift'},
                )
                if created:
                    assignments += 1
                status = 'present' if (day + st.id) % 7 != 0 else 'late'
                Attendance.objects.get_or_create(
                    staff=st, date=d,
                    defaults={'check_in': time(8, 5), 'check_out': time(19, 30), 'status': status},
                )
        self.stdout.write(f'  Shift assignments: {assignments} | '
                          f'Attendance rows: {Attendance.objects.count()}')

        if not LeaveRequest.objects.filter(reason__startswith='DEMO-').exists():
            LeaveRequest.objects.get_or_create(
                staff=self.nurse, leave_type='sick',
                start_date=self.today - timedelta(days=5),
                end_date=self.today - timedelta(days=3),
                defaults={'reason': 'DEMO- Viral fever', 'status': 'approved', 'approved_by': self.admin},
            )
        self.stdout.write(f'  Leave requests: {LeaveRequest.objects.filter(reason__startswith="DEMO-").count()}')

        run, _ = PayrollRun.objects.get_or_create(
            month=self.today.month, year=self.today.year,
            defaults={'status': 'paid', 'processed_by': self.admin,
                      'processed_at': self.now, 'total_amount': Decimal('0')},
        )
        if not run.items.exists():
            total = Decimal('0')
            for i, st in enumerate(staff):
                basic = Decimal(str(40000 + (st.id % 5) * 10000))
                allowances = Decimal(str(5000 + (st.id % 3) * 2000))
                deductions = Decimal(str(2000 + (st.id % 4) * 1000))
                item = PayrollItem.objects.create(
                    payroll_run=run, staff=st, basic_salary=basic,
                    allowances=allowances, deductions=deductions, commission=Decimal('0'),
                )
                total += item.net_salary
            run.total_amount = total
            run.save(update_fields=['total_amount'])
        self.stdout.write(f'  Payroll run: {run} | Items: {run.items.count()}')

        if not DoctorCommission.objects.exists():
            inv = Invoice.objects.filter(status='paid').first()
            if inv and self.doctor:
                DoctorCommission.objects.create(
                    doctor=self.doctor, invoice=inv,
                    procedure_amount=inv.total_amount, commission_rate=Decimal('10.00'),
                )
                inv2 = Invoice.objects.filter(status='paid').exclude(id=inv.id).first()
                if inv2 and self.doctor2:
                    DoctorCommission.objects.create(
                        doctor=self.doctor2, invoice=inv2,
                        procedure_amount=inv2.total_amount, commission_rate=Decimal('10.00'),
                    )
        self.stdout.write(f'  Doctor commissions: {DoctorCommission.objects.count()}')

    def _print_summary(self):
        with tenant_schema_context(self.hospital.schema_name):
            from apps.patients.models import Patient, Allergy, VitalSign
            from apps.appointments.models import Appointment, QueueEntry
            from apps.clinical.models import Visit, Prescription, Admission, NursingNote
            from apps.laboratory.models import LabTestRequest, TestResult, LabReport
            from apps.pharmacy.models import DrugBatch, PurchaseOrder, Dispense, StockMovement
            from apps.billing.models import Invoice, Payment, InsuranceClaim
            from apps.hr.models import StaffShiftAssignment, Attendance, PayrollItem, DoctorCommission

            self.stdout.write(self.style.SUCCESS('\n=== Demo data summary ==='))
            self.stdout.write(f'  Patients:          {Patient.objects.count()} (allergies: {Allergy.objects.count()}, vitals: {VitalSign.objects.count()})')
            self.stdout.write(f'  Appointments:      {Appointment.objects.count()} | Queue today: {QueueEntry.objects.filter(created_at__date=self.today).count()}')
            self.stdout.write(f'  Visits:            {Visit.objects.count()} | Prescriptions: {Prescription.objects.count()} | Admissions: {Admission.objects.count()} (nursing notes: {NursingNote.objects.count()})')
            self.stdout.write(f'  Lab requests:      {LabTestRequest.objects.count()} | Results: {TestResult.objects.count()} | Reports: {LabReport.objects.count()}')
            self.stdout.write(f'  Drug batches:      {DrugBatch.objects.count()} | Purchase orders: {PurchaseOrder.objects.count()} | Dispenses: {Dispense.objects.count()} | Stock movements: {StockMovement.objects.count()}')
            self.stdout.write(f'  Invoices:          {Invoice.objects.count()} | Payments: {Payment.objects.count()} | Claims: {InsuranceClaim.objects.count()}')
            self.stdout.write(f'  HR:                shift assignments {StaffShiftAssignment.objects.count()} | attendance {Attendance.objects.count()} | payroll items {PayrollItem.objects.count()} | commissions {DoctorCommission.objects.count()}')
            self.stdout.write(self.style.SUCCESS('\nSeed complete. Refresh the demo tenant pages.'))
