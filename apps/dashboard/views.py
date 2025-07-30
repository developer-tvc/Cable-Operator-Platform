from django.db.models import Count, Q, Prefetch
from datetime import date, timedelta
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from calendar import monthrange
from django.utils.timezone import now
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from datetime import date, timedelta
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView,DeleteView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from urllib.parse import quote_plus
from django.utils.timezone import now
from apps.accounts.models import Customer
from apps.payments.models import Payment
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


# MIXINS

class CustomerSearchFilterMixin:
    def apply_filters(self, request, queryset):
        status_filter = request.GET.get('status')
        plan_filter = request.GET.get('plan')
        search_query = request.GET.get('search')

        if status_filter in ['active', 'inactive']:
            queryset = queryset.filter(status=status_filter)

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(customer_id__icontains=search_query) |
                Q(mobile__icontains=search_query)
            )

        return queryset, status_filter, plan_filter, search_query

    def filter_by_latest_plan_type(self, customers, plan_type):
        if plan_type not in ['base', 'add_on']:
            return customers

        return [
            c for c in customers
            if hasattr(c, 'latest_subscriptions') and
               c.latest_subscriptions and
               c.latest_subscriptions[0].plan and
               c.latest_subscriptions[0].plan.plan_type == plan_type
        ]


class CustomerDataMixin:
    def get_enriched_customer_data(self, customers):
        customer_data = []

        for customer in customers:
            # Safely fallback if latest_subscriptions not present
            subscriptions = getattr(customer, 'latest_subscriptions', customer.subscriptions.all())
            latest_sub = next(iter(subscriptions), None)

            plan_details = (
                f"{latest_sub.plan.name} - ₹{latest_sub.plan.price}"
                if latest_sub and latest_sub.plan else "No Plan"
            )
            due_amount = latest_sub.plan.price if latest_sub and latest_sub.plan else 0
            last_payment = latest_sub.start_date if latest_sub else "N/A"

            customer_data.append({
                'id': customer.id,
                'customer_id': customer.customer_id,
                'name': customer.name,
                'mobile': customer.mobile,
                'status': customer.status,
                'plan_details': plan_details,
                'due_amount': due_amount,
                'last_payment': last_payment,
            })

        return customer_data

class ExcelExportMixin:
    def export_as_excel(self, request, data, headers, filename='customers.xlsx'):
        if request.GET.get('export') == 'xlsx':
            wb = Workbook()
            ws = wb.active
            ws.title = "Customers"

            # Write header
            for col_num, header in enumerate(headers, 1):
                col_letter = get_column_letter(col_num)
                ws[f"{col_letter}1"] = header

            # Write rows
            for row_num, row_data in enumerate(data, 2):
                for col_num, cell_value in enumerate(row_data, 1):
                    col_letter = get_column_letter(col_num)
                    ws[f"{col_letter}{row_num}"] = cell_value

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            wb.save(response)
            return response
        return None

# Admin Dashboard View
class AdminDashboardView(LoginRequiredMixin, CustomerSearchFilterMixin, CustomerDataMixin, ExcelExportMixin, View):
    login_url = reverse_lazy('dashboard:admin_login')

    def get(self, request):
        form = CustomerForm()
        welcome = request.session.pop('just_logged_in', False)

        sub_qs = Subscription.objects.select_related('plan').order_by('-start_date')
        customers_qs = Customer.objects.prefetch_related(
            Prefetch('subscriptions', queryset=sub_qs, to_attr='latest_subscriptions')
        )

        customers_qs, status_filter, plan_filter, search_query = self.apply_filters(request, customers_qs)
        customers_qs = self.filter_by_latest_plan_type(customers_qs, plan_filter)
        enriched_customers = self.get_enriched_customer_data(customers_qs)
        excel_data = [
            [
                c['customer_id'],
                c['name'],
                c['mobile'],
                c['status'],
                c['plan_details'],
                c['due_amount'],
                c['last_payment']
            ]
            for c in enriched_customers
        ]
        excel_headers = ['Customer ID', 'Name', 'Mobile', 'Status', 'Plan', 'Due Amount', 'Last Payment']

        excel_response = self.export_as_excel(request, excel_data, excel_headers)
        if excel_response:
            return excel_response


        # Dates
        today = now().date()
        tomorrow = today + timedelta(days=1)
        last_day = monthrange(today.year, today.month)[1]
        end_of_month = date(today.year, today.month, last_day)

        # Customers who paid successfully from tomorrow till end of month
        paid_ids_upcoming = set(
            Payment.objects.filter(
                status='success',
                payment_for_month__range=(tomorrow, end_of_month)
            ).values_list('customer_id', flat=True)
        )

        # Customers who paid successfully today or earlier
        paid_ids_current = set(
            Payment.objects.filter(
                status='success',
                payment_for_month__lte=today
            ).values_list('customer_id', flat=True)
        )

        # Upcoming dues: Active customers who haven't paid for upcoming months
        upcoming_dues_count = Customer.objects.filter(
            status='active'
        ).exclude(id__in=paid_ids_upcoming).count()

        # Overdue: Active customers who haven't paid until today (including today)
        overdue_customers_count = Customer.objects.filter(
            status='active'
        ).exclude(id__in=paid_ids_current).count()

        # Counts for summary
        customer_counts = Customer.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status='active')),
            inactive=Count('id', filter=Q(status='inactive'))
        )

        return render(request, 'dashboard/dashboard.html', {
            'form': form,
            'welcome': welcome,
            'total_customers': customer_counts['total'],
            'active_customers': customer_counts['active'],
            'inactive_customers': customer_counts['inactive'],
            'overdue_customers': overdue_customers_count,
            'upcoming_dues': upcoming_dues_count,
            'customers': enriched_customers,
            'status': status_filter,
            'plan': plan_filter,
            'search': search_query,
        })

# Create Customer View
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

class CustomerListView(LoginRequiredMixin, CustomerDataMixin, ListView):
    model = Customer
    template_name = 'dashboard/Customer-Management.html'
    context_object_name = 'customers'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CustomerForm()
        context['customers'] = self.get_enriched_customer_data(context['customers'])
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
