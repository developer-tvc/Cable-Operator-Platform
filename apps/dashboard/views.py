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
# # Admin Dashboard
# class AdminDashboardView(LoginRequiredMixin, TemplateView):
#     login_url = 'dashboard:admin_login'
#     template_name = 'admin_login.html'
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['total_customers'] = Customer.objects.count()
#         context['active_customers'] = Customer.objects.filter(status='active').count()
#         return context
#
# # Customer List
# class CustomerListView(LoginRequiredMixin, ListView):
#     login_url = 'dashboard:admin_login'
#     model = Customer
#     template_name = 'customer_detail.html'
#     context_object_name = 'customers'
#
# # Customer Create
# class CustomerCreateView(LoginRequiredMixin, CreateView):
#     login_url = 'dashboard:admin_login'
#     model = Customer
#     form_class = CustomerForm
#     template_name = 'customer_add.html'
#     success_url = reverse_lazy('dashboard:customer_list')
#
# # Customer Update
# class CustomerUpdateView(LoginRequiredMixin, UpdateView):
#     login_url = 'dashboard:admin_login'
#     model = Customer
#     form_class = CustomerForm
#     template_name = 'customer_edit.html'
#     success_url = reverse_lazy('dashboard:customer_list')
#
# # Customer Delete
# class CustomerDeleteView(LoginRequiredMixin, DeleteView):
#     login_url = 'dashboard:admin_login'
#     model = Customer
#     success_url = reverse_lazy('dashboard:customer_list')
#     template_name = 'customer_delete.html'
#
# # Customer Status Toggle
# class CustomerToggleStatusView(LoginRequiredMixin, View):
#     login_url = 'dashboard:admin_login'
#
#     def get(self, request, pk):
#         customer = Customer.objects.get(pk=pk)
#         customer.status = 'inactive' if customer.status == 'active' else 'active'
#         customer.save()
#         return redirect('dashboard:customer_list')
