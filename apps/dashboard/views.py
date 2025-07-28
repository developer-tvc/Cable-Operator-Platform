from django.db.models import Count, Q
from datetime import date, timedelta
from calendar import monthrange
from django.utils.timezone import now
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from apps.accounts.models import AdminUser, Customer
from apps.payments.models import Payment
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

class AdminDashboardView(LoginRequiredMixin, View):
    login_url = reverse_lazy('dashboard:admin_login')

    def get(self, request):
        form = CustomerForm()
        welcome = request.session.pop('just_logged_in', False)

        customer_counts = Customer.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status='active')),
            inactive=Count('id', filter=Q(status='inactive'))
        )

        today = now().date()
        tomorrow = today + timedelta(days=1)
        last_day = monthrange(today.year, today.month)[1]
        end_of_month = date(today.year, today.month, last_day)

        paid_ids_upcoming = Payment.objects.filter(
            status='success',
            payment_for_month__range=(tomorrow, end_of_month)
        ).values_list('customer_id', flat=True)

        upcoming_dues_count = Customer.objects.filter(
            status='active'
        ).exclude(id__in=paid_ids_upcoming).count()


        paid_customers_ids = Payment.objects.filter(
            status='success',
            payment_for_month__lte=today
        ).values_list('customer_id', flat=True)

        overdue_customers_count = Customer.objects.filter(
            status='active'
        ).exclude(id__in=paid_customers_ids).count()

        return render(request, 'dashboard/dashboard.html', {
            'form': form,
            'welcome': welcome,
            'total_customers': customer_counts['total'],
            'active_customers': customer_counts['active'],
            'inactive_customers': customer_counts['inactive'],
            'overdue_customers': overdue_customers_count,
            'upcoming_dues': upcoming_dues_count,
        })

    
# Customer List View    
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'dashboard/customer_list.html'
    context_object_name = 'customers'

    def get_queryset(self):
        return Customer.objects.filter(status='active')
      

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
        customer = Customer.objects.filter(pk=pk, status='active').first()
        if customer:
            customer.deactivate()
            messages.success(request, "Customer deactivated successfully.")
        else:
            messages.error(request, "Customer not found or already inactive.")
        return redirect('dashboard:customer_list')
