from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model

from apps.core.form_helpers import style_form
from apps.users.models import Role

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Username or email',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Password',
        })
    )


class OTPVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full text-center text-2xl tracking-widest',
            'placeholder': '000000',
            'maxlength': '6',
        })
    )


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Email address',
        })
    )


class StaffCreateForm(UserCreationForm):
    role = forms.ChoiceField(choices=User.Role.choices if hasattr(User, 'Role') else [])
    phone = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'phone', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [(r, label) for r, label in Role.choices if r != Role.PATIENT]
        self.fields['role'].choices = choices
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'input input-bordered w-full'


class StaffEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'phone', 'is_active')
        widgets = {
            'role': forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [
            (r, label) for r, label in Role.choices if r != Role.PATIENT
        ]
        style_form(self)
