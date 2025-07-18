from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from apps.accounts.models import AdminUser, Customer
from .forms import CustomerForm
from .forms import AdminLoginForm

# Admin Login View
class AdminLoginView(View):
    template_name = 'dashboard/admin_login.html'

    def get(self, request):
        form = AdminLoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard:admin_dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
        return render(request, self.template_name, {'form': form})
