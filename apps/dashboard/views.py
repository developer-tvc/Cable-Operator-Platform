from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from datetime import date, timedelta
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView,DeleteView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from urllib.parse import quote_plus
from django.utils.timezone import now
from apps.accounts.models import Customer
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from .forms import CustomerForm
from .forms import AdminLoginForm
from apps.subscriptions.models import Subscription
from apps.plans.models import Plan
from apps.dashboard.utils import generate_customer_qr

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
        return render(request, 'dashboard/Dashboard.html', {'form': form, 'welcome': welcome})

class CreateCustomerView(LoginRequiredMixin, View):
    login_url = reverse_lazy('dashboard:admin_login')
    template_name = 'dashboard/Customer-Management.html'

    def get(self, request):
        form = CustomerForm()
        customers = Customer.objects.all()
        base_plans = Plan.objects.filter(plan_type='base')
        add_on_plans = Plan.objects.filter(plan_type='add_on')

        return render(request, self.template_name, {
            'form': form,
            'customers': customers,
            'base_plans': base_plans,
            'add_on_plans': add_on_plans,
        })

    def post(self, request):
        form = CustomerForm(request.POST)
        customers = Customer.objects.all()

        print("POST DATA:", request.POST)
        print("Is form valid?", form.is_valid())
        print("Form errors:", form.errors)

        if form.is_valid():
            customer = form.save(commit=False)
            customer.save()
            form.save_m2m()
            print("Customer created:", customer)

            base = form.cleaned_data.get('base_plan')
            addons = form.cleaned_data.get('add_on_plan')
            today = date.today()

            if base:
                Subscription.objects.create(
                    customer=customer,
                    plan=base,
                    start_date=today,
                    end_date=today + timedelta(days=base.duration_days)
                )
            if addons:
                for plan in addons:
                    Subscription.objects.create(
                        customer=customer,
                        plan=plan,
                        start_date=today,
                        end_date=today + timedelta(days=plan.duration_days)
                    )

            generate_customer_qr(customer, request)

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': f"Customer {customer.customer_id} created."})
            messages.success(request, f"Customer {customer.customer_id} created.")
            return redirect('dashboard:customer_list')

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid form data.'})
        messages.error(request, "Failed to create customer.")
        return render(request, self.template_name, {
            'form': form,
            'customers': customers,
        })

class PlanInfoView(View):
    def get(self, request):
        base_id = request.GET.get('base_plan')
        addon_ids = request.GET.get('add_on_plan', '')
        total = 0
        days = None

        # Base plan calculation
        if base_id:
            base = Plan.objects.filter(pk=base_id, plan_type='base').first()
            if base:
                total += float(base.price)
                days = base.duration_days

        # Add-on plans
        if addon_ids:
            addon_id_list = [int(i) for i in addon_ids.split(',') if i.isdigit()]
            addons = Plan.objects.filter(pk__in=addon_id_list, plan_type='add_on')
            for addon in addons:
                total += float(addon.price)
                if not days:
                    days = addon.duration_days

        due_date = (date.today() + timedelta(days=days)).isoformat() if days else ''
        return JsonResponse({
            'due_amount': f"{total:.2f}",
            'due_date': due_date,
        })

class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'dashboard/Customer-Management.html'
    context_object_name = 'customers'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer_data = []

        for customer in context['customers']:
            latest_sub = Subscription.objects.filter(customer=customer).order_by('-start_date').first()

            plan_details = f"{latest_sub.plan.name} - ₹{latest_sub.plan.price}" if latest_sub and latest_sub.plan else "No Plan"
            due_amount = latest_sub.plan.price if latest_sub and latest_sub.plan else 0
            last_payment = latest_sub.start_date if latest_sub else "N/A"

            customer_data.append({
                'customer_id': customer.customer_id,
                'name': customer.name,
                'mobile': customer.mobile,
                'status': customer.status,
                'plan_details': plan_details,
                'due_amount': due_amount,
                'last_payment': last_payment,
            })

        context['form'] = CustomerForm()
        context['customers'] = customer_data
        return context


class GPayRedirectView(View):
    def get(self, request, customer_id):
        customer = get_object_or_404(Customer, customer_id=customer_id)

        today = now().date()
        active_subscriptions = customer.subscriptions.filter(end_date__gte=today)
        due_amount = sum(sub.plan.price for sub in active_subscriptions)

        if due_amount <= 0:
            return render(request, "dashboard/no_due.html", {"customer": customer})

        upi_url = (
            f"upi://pay?"
            f"pa="
            f"&pn={quote_plus('Cable Operator')}"
            f"&am={due_amount:.2f}"
            f"&cu=INR"
            f"&tn=Payment+for+{quote_plus(customer.name)}"
        )
        return redirect(upi_url)

class UpdateCustomerView(LoginRequiredMixin, View):
    login_url = reverse_lazy('dashboard:admin_login')
    template_name = 'dashboard/Customer-Management1.html'

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        subscriptions = Subscription.objects.filter(customer=customer)

        base = subscriptions.filter(plan__plan_type='base').first()
        addon = subscriptions.filter(plan__plan_type='add_on').first()

        initial = {
            'base_plan': base.plan if base else None,
            'add_on_plan': addon.plan if addon else None,
        }

        form = CustomerForm(instance=customer, initial=initial)
        customers = Customer.objects.all()

        context = {
            'form': form,
            'customers': customers,
            'edit_customer_id': customer.pk,
        }

        return render(request, self.template_name, context)

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        form = CustomerForm(request.POST, instance=customer)

        if form.is_valid():
            customer = form.save()

            base = form.cleaned_data.get('base_plan')
            addon = form.cleaned_data.get('add_on_plan')
            today = date.today()

            # Delete existing subscriptions
            Subscription.objects.filter(customer=customer, plan__plan_type='base').delete()
            Subscription.objects.filter(customer=customer, plan__plan_type='add_on').delete()

            # Create updated subscriptions
            if base:
                Subscription.objects.create(
                    customer=customer,
                    plan=base,
                    start_date=today,
                    end_date=today + timedelta(days=base.duration_days)
                )
            if addon:
                Subscription.objects.create(
                    customer=customer,
                    plan=addon,
                    start_date=today,
                    end_date=today + timedelta(days=addon.duration_days)
                )

            messages.success(request, f"Customer {customer.customer_id} updated successfully.")
            return redirect('dashboard:customer_list')

        customers = Customer.objects.all()
        messages.error(request, "Failed to update customer. Please fix the errors below.")

        context = {
            'form': form,
            'customers': customers,
            'edit_customer_id': customer.id,
        }

        return render(request, self.template_name, context)

class CustomerDetailView(LoginRequiredMixin, View):
    template_name = 'dashboard/Customer-Detail.html'

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        subscriptions = Subscription.objects.filter(customer=customer)

        base_plan = subscriptions.filter(plan__plan_type='base').first()
        add_ons = subscriptions.filter(plan__plan_type='add_on')

        context = {
            'customer': customer,
            'base_plan': base_plan.plan if base_plan else None,
            'add_ons': [sub.plan for sub in add_ons],
            'assigned_on': base_plan.start_date if base_plan else None,
            'due_date': base_plan.end_date if base_plan else None,
            'due_amount': base_plan.plan.amount if base_plan else None,
        }
        return render(request, self.template_name, context)

class DeleteCustomerView(LoginRequiredMixin, DeleteView):
    login_url = reverse_lazy('dashboard:admin_login')

    @method_decorator(require_POST)
    def post(self, request, pk):
        customer = Customer.objects.filter(pk=pk, status='active').first()
        if customer:
            customer.soft_delete()
            messages.success(request, "Customer deleted successfully.")
        else:
            messages.error(request, "Customer not found or already deleted.")
        return redirect('dashboard:customer_list')
