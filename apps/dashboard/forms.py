from django import forms
from apps.accounts.models import Customer
from apps.plans.models import Plan

class CustomerForm(forms.ModelForm):
    base_plan = forms.ModelChoiceField(
        queryset=Plan.objects.filter(plan_type='base'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_base_plan'})
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

    class Meta:
        model = Customer
        fields = [
            'name', 'email', 'mobile', 'address',
            'base_plan', 'add_on_plan',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class AdminLoginForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=255)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
