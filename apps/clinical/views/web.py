from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from apps.clinical.forms import VisitForm
from apps.clinical.models import Visit, Ward, Bed
from apps.core.decorators import roles_required


@login_required
def visit_list(request):
    visits = Visit.objects.select_related('patient', 'doctor').order_by('-visit_date')[:50]
    if request.user.role == 'doctor':
        visits = visits.filter(doctor=request.user)
    return render(request, 'clinical/visits.html', {'visits': visits})


@login_required
@roles_required('doctor', 'nurse', 'receptionist', 'admin')
def visit_create(request):
    if request.method == 'POST':
        form = VisitForm(request.POST)
        if form.is_valid():
            visit = form.save()
            messages.success(request, f'Visit created for {visit.patient.full_name}.')
            return redirect('clinical:visit_detail', pk=visit.pk)
        messages.error(request, 'Please correct the errors below.')
    else:
        initial = {}
        if request.user.role == 'doctor':
            initial['doctor'] = request.user.pk
        form = VisitForm(initial=initial)
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': 'New Clinical Visit',
        'back_url': 'clinical:visits',
        'submit_label': 'Start Visit',
    })


@login_required
def visit_detail(request, pk):
    visit = get_object_or_404(Visit.objects.select_related('patient', 'doctor'), pk=pk)
    return render(request, 'clinical/visit_detail.html', {'visit': visit})


@login_required
def ward_list(request):
    wards = Ward.objects.filter(is_active=True).prefetch_related('beds')
    return render(request, 'clinical/wards.html', {'wards': wards})


@login_required
def vitals_chart(request):
    return render(request, 'clinical/vitals.html')
