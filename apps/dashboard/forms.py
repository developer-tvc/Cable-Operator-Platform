from django import forms
from django.contrib.auth import authenticate
from apps.accounts.models import Customer
from apps.plans.models import Plan
from datetime import date

class CustomerForm(forms.ModelForm):
    base_plan = forms.ModelChoiceField(
        queryset=Plan.objects.filter(plan_type='base'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_base_plan', 'data-placeholder': 'Select Base Plans'})

    )

    add_on_plan = forms.ModelMultipleChoiceField(
        queryset=Plan.objects.filter(plan_type='add_on'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select select2',
            'id': 'id_add_on_plan',
            'data-placeholder': 'Select Add-on Plans'
        })
    )

    start_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        }),
        initial=date.today
    )

    class Meta:
        model = Customer
        fields = [
            'name', 'email', 'mobile', 'address',
            'base_plan', 'add_on_plan', 'start_date'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class AdminLoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=255,
        error_messages={
            'required': 'Email is required',
            'invalid': 'Enter a valid email address',
        }
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        error_messages={
            'required': 'Password is required',
        }
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if user is None:
                raise forms.ValidationError("Invalid email or password.")
            if not user.is_active:
                raise forms.ValidationError("This account is inactive.")

        return cleaned_data
