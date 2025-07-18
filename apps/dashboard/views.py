from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from apps.accounts.models import AdminUser, Customer
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
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
                request.session['just_logged_in'] = True
                return redirect('dashboard:admin_dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
        return render(request, self.template_name, {'form': form})
    
# Admin Logout View    
class AdminLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('dashboard:admin_login')

# Admin Dashboard View    
class AdminDashboardView(LoginRequiredMixin, View):
    login_url = reverse_lazy('dashboard:admin_login')

    def get(self, request):
        form = CustomerForm()
        welcome = request.session.pop('just_logged_in', False)
        return render(request, 'dashboard/dashboard.html', {'form': form, 'welcome': welcome})

class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'dashboard/customer_list.html'
    context_object_name = 'customers'

    def get_queryset(self):
        # Only show customers that are not soft-deleted
        return Customer.objects.filter(is_deleted=False)
      

# Create Customer View
class CreateCustomerView(LoginRequiredMixin, View):
    login_url = reverse_lazy('dashboard:admin_login')
    template_name = 'dashboard/customer_form.html'

    def get(self, request):
        form = CustomerForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer created successfully.")
            return redirect('dashboard:customer_list')
        else:
            messages.error(request, "Failed to create customer. Please fix the errors.")
        return render(request, self.template_name, {'form': form})

    
# Update Customer View
class UpdateCustomerView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'dashboard/customer_form.html'
    success_url = reverse_lazy('dashboard:customer_list')

# Delete Customer View
class DeleteCustomerView(LoginRequiredMixin, DeleteView):
    login_url = reverse_lazy('dashboard:admin_login')

    @method_decorator(require_POST)
    def post(self, request, pk):
        customer = Customer.objects.filter(pk=pk, is_deleted=False).first()
        if customer:
            customer.soft_delete()
            messages.success(request, "Customer deleted successfully.")
        else:
            messages.error(request, "Customer not found or already deleted.")
        return redirect('dashboard:customer_list')
