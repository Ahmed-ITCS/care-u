from django.conf import settings
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages

from apps.core.permissions import IsAdmin
from apps.core.list_filters import filter_list_context
from apps.tenants.limits import check_staff_limit, SubscriptionLimitExceeded
from apps.users.filters import StaffUserFilter
from apps.users.forms import LoginForm, OTPVerifyForm, PasswordResetRequestForm, StaffCreateForm, StaffEditForm
from apps.users.models import User, OTPVerification
from apps.users.tasks import send_otp_email, send_otp_sms


class GPHLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get(self, request, *args, **kwargs):
        # All hospitals use the single public login — no per-tenant login page
        return redirect(settings.LOGIN_URL)


def logout_view(request):
    """Tenant-prefixed logout — delegates to public sign-out logic."""
    from apps.tenants.views.public import public_logout
    return public_logout(request)


def otp_request_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        channel = request.POST.get('channel', 'email')
        try:
            user = User.objects.get(username=username)
            otp = OTPVerification.generate(user, purpose='login', channel=channel)
            if channel == 'sms' and user.phone:
                send_otp_sms.delay(user.phone, otp.code)
            else:
                send_otp_email.delay(user.id, otp.code)
            request.session['otp_username'] = username
            messages.success(request, f'OTP sent via {channel}')
            return redirect('users:otp_verify')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
    return render(request, 'users/otp_request.html')


def otp_verify_view(request):
    username = request.session.get('otp_username')
    if not username:
        return redirect('users:otp_request')

    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            user = get_object_or_404(User, username=username)
            otp = OTPVerification.objects.filter(
                user=user, purpose='login', is_used=False
            ).first()
            if otp and otp.verify(form.cleaned_data['code']):
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                user.is_verified = True
                user.save(update_fields=['is_verified'])
                del request.session['otp_username']
                return redirect('core:dashboard')
            messages.error(request, 'Invalid or expired OTP')
    else:
        form = OTPVerifyForm()
    return render(request, 'users/otp_verify.html', {'form': form})


def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.get(email=form.cleaned_data['email'])
                otp = OTPVerification.generate(user, purpose='password_reset')
                send_otp_email.delay(user.id, otp.code, 'password_reset')
                request.session['reset_email'] = user.email
                messages.success(request, 'Reset code sent to your email')
                return redirect('users:password_reset_confirm')
            except User.DoesNotExist:
                messages.error(request, 'No account with that email')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'users/password_reset.html', {'form': form})


def password_reset_confirm(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('users:password_reset')

    if request.method == 'POST':
        code = request.POST.get('code')
        new_password = request.POST.get('new_password')
        try:
            user = User.objects.get(email=email)
            otp = OTPVerification.objects.filter(
                user=user, purpose='password_reset', is_used=False
            ).first()
            if otp and otp.verify(code):
                user.set_password(new_password)
                user.save()
                del request.session['reset_email']
                messages.success(request, 'Password reset successful')
                return redirect(settings.LOGIN_URL)
            messages.error(request, 'Invalid or expired code')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
    return render(request, 'users/password_reset_confirm.html')


@login_required
def staff_list(request):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied')
        return redirect('core:dashboard')
    queryset = User.objects.exclude(role='patient').select_related('staff_profile', 'doctor_profile')
    ctx = filter_list_context(
        request, queryset, StaffUserFilter, limit=100, clear_url=reverse('users:staff_list'),
    )
    ctx['staff'] = ctx.pop('items')
    return render(request, 'users/staff_list.html', ctx)


@login_required
def staff_create(request):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied')
        return redirect('core:dashboard')
    if request.method == 'POST':
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            try:
                check_staff_limit()
            except SubscriptionLimitExceeded as exc:
                messages.error(request, str(exc.detail))
            else:
                form.save()
                messages.success(request, 'Staff member created')
                return redirect('users:staff_list')
    else:
        form = StaffCreateForm()
    return render(request, 'users/staff_form.html', {'form': form})


@login_required
def staff_edit(request, pk):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied')
        return redirect('core:dashboard')
    user = get_object_or_404(User, pk=pk)
    if user.role == 'patient':
        messages.error(request, 'Cannot edit patient accounts here.')
        return redirect('users:staff_list')
    if request.method == 'POST':
        form = StaffEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            from apps.tenants.middleware import ensure_request_tenant
            from apps.tenants.auth import sync_user_to_index
            tenant = ensure_request_tenant(request)
            if tenant:
                sync_user_to_index(tenant, user)
            messages.success(request, 'Staff member updated.')
            return redirect('users:staff_list')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffEditForm(instance=user)
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': f'Edit {user.get_full_name() or user.username}',
        'back_url': 'users:staff_list',
        'submit_label': 'Save Changes',
    })
