from django.db import models
from django.db.models import Count, Q, Prefetch, Sum
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from calendar import monthrange
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from datetime import date, timedelta, datetime as dt
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.utils.timezone import now, make_aware
from apps.accounts.models import Customer
from apps.payments.models import Payment
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from .forms import CustomerForm
from .forms import AdminLoginForm
from apps.subscriptions.models import Subscription
from apps.plans.models import Plan
from apps.dashboard.utils import generate_customer_qr
import razorpay
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle
import json
from dateutil.relativedelta import relativedelta
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal,ROUND_HALF_UP
from django.utils import timezone
from datetime import datetime


# Admin Login View
class AdminLoginView(View):
    template_name = 'accounts/Login.html'

    def get(self, request):
        form = AdminLoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            # Credentials already validated in form's clean()
            user = authenticate(
                request,
                username=form.cleaned_data['email'],  # Or just email
                password=form.cleaned_data['password']
            )
            if user:
                login(request, user)
                request.session['just_logged_in'] = True
                return redirect('dashboard:admin_dashboard')
        else:
            messages.error(request, 'Login failed. Please correct the errors below.')

        return render(request, self.template_name, {'form': form})

# Admin Logout View
class AdminLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('dashboard:admin_login')

# Mixins
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

# class CustomerDataMixin:
#     def get_enriched_customer_data(self, customers):
#         customer_data = []
#         today = timezone.now().date()
#
#         # First & last day of current month
#         month_start = date(today.year, today.month, 1)
#         last_day = monthrange(today.year, today.month)[1]
#         month_end = date(today.year, today.month, last_day)
#
#         # Aware datetimes
#         start_of_month = timezone.make_aware(dt.combine(month_start, dt.min.time()))
#         end_of_month = timezone.make_aware(dt.combine(month_end, dt.max.time()))
#
#         for customer in customers:
#             active_subs = customer.subscriptions.filter(is_active=True).select_related('plan')
#
#             due_amount = Decimal("0.00")
#             plan_list = []
#
#             for sub in active_subs:
#                 # Use revised amount if set, else use plan price
#                 amount = Decimal(sub.revised_amount) if sub.revised_amount else Decimal(sub.plan.price)
#                 due_amount += amount
#                 plan_list.append(f"{sub.plan.name} (₹{amount:.2f})")
#
#             # Last successful payment
#             last_payment = Payment.objects.filter(
#                 customer=customer, status='success'
#             ).order_by('-payment_date').first()
#
#             last_payment_display = (
#                 last_payment.payment_date.strftime('%d-%b-%Y')
#                 if last_payment and last_payment.payment_date else 'N/A'
#             )
#
#             # Payment status
#             if Payment.objects.filter(
#                 customer=customer,
#                 payment_date__range=(start_of_month, end_of_month),
#                 status='success'
#             ).exists():
#                 payment_status = "No Dues"
#             else:
#                 payment_status = "Due"
#
#             customer_data.append({
#                 'id': customer.id,
#                 'customer_id': customer.customer_id,
#                 'name': customer.name,
#                 'mobile': customer.mobile,
#                 'status': customer.status,
#                 'plan_details': plan_list,
#                 'due_amount': f"{due_amount:.2f}",
#                 'final_amount': f"{due_amount:.2f}",
#                 'last_payment': last_payment,
#                 'payment_status': payment_status,
#                 'total_revised_amount': f"{due_amount:.2f}",
#                 'qr_code_url': (
#                     customer.qr_code.image.url
#                     if hasattr(customer, 'qr_code') and customer.qr_code and customer.qr_code.image
#                     else None
#                 ),
#             })
#
#         return customer_data

def calculate_due_and_status(customer):
    today = timezone.now().date()
    active_subs = customer.subscriptions.filter(is_active=True, end_date__gte=today)

    current_due = sum([
        sub.revised_amount if sub.revised_amount else sub.plan.price
        for sub in active_subs
    ], Decimal(0))

    last_payment = customer.payments.filter(
        payment_date__month=today.month,
        payment_date__year=today.year,
        status='success'
    ).order_by('-payment_date').first()

    paid_amount = last_payment.amount if last_payment else Decimal(0)
    due_amount = max(current_due - paid_amount, Decimal(0))

    payment_status = "No Dues" if due_amount == 0 else f"Due"

    return {
        "due_amount": due_amount,
        "payment_status": payment_status
    }

class CustomerDataMixin:
    def get_enriched_customer_data(self, customers):
        customer_data = []
        today = timezone.now().date()

        for customer in customers:
            active_subs = customer.subscriptions.filter(is_active=True).select_related('plan')

            # ✅ Use helper for due + payment status
            due_info = calculate_due_and_status(customer)

            plan_list = [
                f"{sub.plan.name} (₹{sub.revised_amount if sub.revised_amount else sub.plan.price})"
                for sub in active_subs
            ]

            # Last successful payment
            last_payment = Payment.objects.filter(
                customer=customer, status='success'
            ).order_by('-payment_date').first()

            last_payment_display = (
                last_payment.payment_date.strftime('%d-%b-%Y')
                if last_payment and last_payment.payment_date else 'N/A'
            )

            customer_data.append({
                'id': customer.id,
                'customer_id': customer.customer_id,
                'name': customer.name,
                'mobile': customer.mobile,
                'status': customer.status,
                'plan_details': plan_list,

                # ✅ Pull values from helper
                'due_amount': f"{due_info['due_amount']:.2f}",
                'final_amount': f"{due_info['due_amount']:.2f}",
                'payment_status': due_info['payment_status'],
                'total_revised_amount': f"{due_info['due_amount']:.2f}",

                'last_payment': last_payment,
                'qr_code_url': (
                    customer.qr_code.image.url
                    if hasattr(customer, 'qr_code') and customer.qr_code and customer.qr_code.image
                    else None
                ),
            })

        return customer_data


class ExcelExportMixin:
    def export_as_excel(self, request, data, headers, filename='customers.xlsx'):
        wb = Workbook()
        ws = wb.active
        ws.title = "Sheet1"

        # Write headers
        for col_num, header in enumerate(headers, 1):
            col_letter = get_column_letter(col_num)
            ws[f"{col_letter}1"] = header

        # Write data
        for row_num, row_data in enumerate(data, 2):
            for col_num, cell_value in enumerate(row_data, 1):
                col_letter = get_column_letter(col_num)

                # Convert lists to comma-separated string
                if isinstance(cell_value, list):
                    cell_value = ', '.join(map(str, cell_value))
                # Convert model instances to string (safety)
                elif hasattr(cell_value, '__str__'):
                    cell_value = str(cell_value)

                ws[f"{col_letter}{row_num}"] = cell_value

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response

class PaymentSearchFilterMixin:
    def apply_payment_filters(self, request, queryset):
        status_filter = request.GET.get('status')
        pay_search_query = request.GET.get('pay_search')

        if status_filter in ['success', 'initiated', 'failed']:
            queryset = queryset.filter(status=status_filter)

        if pay_search_query:
            queryset = queryset.filter(
                Q(customer__name__icontains=pay_search_query) |
                Q(customer__customer_id__icontains=pay_search_query) |
                Q(customer__mobile__icontains=pay_search_query)
            )

        return queryset, status_filter, pay_search_query

# Admin Dashboard View
class AdminDashboardView(LoginRequiredMixin,CustomerSearchFilterMixin,CustomerDataMixin,
ExcelExportMixin,PaymentSearchFilterMixin,View):
    login_url = reverse_lazy('dashboard:admin_login')

    def get(self, request):
        form = CustomerForm()
        welcome = request.session.pop('just_logged_in', False)

        # ----- Customers -----
        sub_qs = Subscription.objects.select_related('plan').order_by('-start_date')
        customers_qs = Customer.objects.prefetch_related(
            Prefetch('subscriptions', queryset=sub_qs, to_attr='latest_subscriptions')
        )

        customers_qs, status_filter, plan_filter, search_query = self.apply_filters(request, customers_qs)
        customers_qs = self.filter_by_latest_plan_type(customers_qs, plan_filter)
        enriched_customers = self.get_enriched_customer_data(customers_qs)

        # ----- Excel Export for Customers -----
        if request.GET.get('export') == 'customers_xlsx':
            excel_data = [
                [
                    c['customer_id'],
                    c['name'],
                    c['mobile'],
                    ", ".join(c['plan_details']),
                    c['payment_status'],
                    float(c['due_amount']),  # ensure number
                    c['status'],
                    c['last_payment'].payment_date.strftime('%d-%b-%Y') if c['last_payment'] else 'N/A',
                ]
                for c in enriched_customers
            ]
            excel_headers = [
                'Customer ID', 'Name', 'Mobile', 'Plan Details',
                'Payment Status', 'Due Amount', 'Customer Status', 'Last Payment'
            ]
            return self.export_as_excel(request, excel_data, excel_headers, filename='customers.xlsx')

        # ----- Recent Payments -----
        payments_qs = (Payment.objects.select_related('customer').filter(customer__status='active').order_by('-payment_date'))
        payments_qs, pay_status, pay_search_query = self.apply_payment_filters(request, payments_qs)

        # ----- Excel Export for Payments -----
        if request.GET.get('export') == 'payments_xlsx':
            payment_excel_data = [
                [
                    str(p.customer.customer_id),
                    str(p.customer.name),
                    str(p.customer.mobile),
                    float(p.amount),
                    str(p.status),
                    p.payment_date.strftime('%d-%b-%Y') if p.payment_date else 'N/A'
                ]
                for p in payments_qs
            ]
            payment_excel_headers = ['Customer ID', 'Name', 'Mobile', 'Amount', 'Status', 'Payment Date']

            return self.export_as_excel(request, payment_excel_data, payment_excel_headers, filename='payments.xlsx')

        # ----- Limit Recent Payments -----
        recent_payments = payments_qs.filter(status__in=["success", "initiated", "failed"])[:10]

        # ----- Counts & Dashboard Data -----
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)

        # Month boundaries (aware datetimes)
        first_day_of_month = today.replace(day=1)
        last_day_of_month = date(today.year, today.month, monthrange(today.year, today.month)[1])
        start_of_month = timezone.make_aware(dt.combine(first_day_of_month, dt.min.time()))
        end_of_month = timezone.make_aware(dt.combine(last_day_of_month, dt.max.time()))
        end_of_today = timezone.make_aware(dt.combine(today, dt.max.time()))
        start_of_tomorrow = timezone.make_aware(dt.combine(tomorrow, dt.min.time()))

        # Preload active & inactive customer IDs
        active_customer_ids = set(Customer.objects.filter(status='active').values_list('id', flat=True))
        inactive_count = Customer.objects.filter(status='inactive').count()

        # Paid customers for this month (only active ones matter here)
        already_paid_ids = set(
            Payment.objects.filter(
                status='success',
                customer_id__in=active_customer_ids,
                payment_date__range=(start_of_month, end_of_today)
            ).values_list('customer_id', flat=True)
        )

        # Overdue = active customers not paid by today
        overdue_customers_count = len(active_customer_ids - already_paid_ids)

        # Paid customers later this month (active only)
        paid_ids_upcoming = set(
            Payment.objects.filter(
                status='success',
                customer_id__in=active_customer_ids,
                payment_date__range=(start_of_tomorrow, end_of_month)
            ).values_list('customer_id', flat=True)
        )

        # Upcoming dues = active customers who haven't paid at all this month
        upcoming_dues_count = len(active_customer_ids - already_paid_ids - paid_ids_upcoming)

        # Monthly revenue = all successful payments in current month (active & inactive)
        monthly_revenue = Payment.objects.filter(
            status='success',
            payment_date__range=(start_of_month, end_of_month)
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Customer counts
        customer_counts = {
            'total': len(active_customer_ids) + inactive_count,
            'active': len(active_customer_ids),
            'inactive': inactive_count
        }

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
            'recent_payments': recent_payments,
            'pay_status': pay_status,
            'pay_search': pay_search_query,
            'monthly_revenue': monthly_revenue,
        })

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

        if form.is_valid():
            customer = form.save(commit=False)
            customer.save()
            form.save_m2m()

            base = form.cleaned_data.get('base_plan')
            addons = form.cleaned_data.get('add_on_plan')
            start_date = form.cleaned_data.get('start_date')

            # Revised amount from user input
            revised_amount_input = request.POST.get('revised_amount')
            revised_amount = Decimal(revised_amount_input) if revised_amount_input else None

            selected_plans = []
            if base:
                selected_plans.append(base)
            if addons:
                selected_plans.extend(addons)

            total_original = sum(plan.price for plan in selected_plans)

            for plan in selected_plans:
                original_price = plan.price
                duration = plan.duration_days
                end_date = start_date + timedelta(days=duration)

                if revised_amount is not None and total_original:
                    proportion = Decimal(original_price) / Decimal(total_original)
                    revised_plan_amount = (revised_amount * proportion).quantize(Decimal('0.01'),
                                                                                 rounding=ROUND_HALF_UP)
                else:
                    revised_plan_amount = None

                Subscription.objects.create(
                    customer=customer,
                    plan=plan,
                    start_date=start_date,
                    end_date=end_date,
                    revised_amount=revised_plan_amount
                )

            generate_customer_qr(customer, request)

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': f"Customer {customer.customer_id} created."})

            messages.success(request, f"Customer {customer.customer_id} created.")
            return redirect('dashboard:customer_list')

        # On error
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

class CustomerListView(LoginRequiredMixin, CustomerSearchFilterMixin, CustomerDataMixin, ExcelExportMixin,
ListView
):
    model = Customer
    template_name = 'dashboard/Customer-Management.html'
    context_object_name = 'customers'

    def get(self, request, *args, **kwargs):
        # Base queryset
        sub_qs = Subscription.objects.select_related('plan').order_by('-start_date')
        customers_qs = Customer.objects.prefetch_related(
            Prefetch('subscriptions', queryset=sub_qs, to_attr='latest_subscriptions')
        )

        # Apply search & filters
        customers_qs, status_filter, plan_filter, search_query = self.apply_filters(request, customers_qs)
        customers_qs = self.filter_by_latest_plan_type(customers_qs, plan_filter)

        # Enriched customer data
        enriched_customers = self.get_enriched_customer_data(customers_qs)

        # Export to .xlsx
        if request.GET.get('export') == 'xlsx':
            excel_data = [
                [
                    c['customer_id'],
                    c['name'],
                    c['mobile'],
                    c['status'],
                    c['plan_details'],
                    c['due_amount'],
                    c['last_payment'],
                ]
                for c in enriched_customers
            ]
            headers = [
                'Customer ID', 'Name', 'Mobile', 'Status',
                'Plan', 'Due Amount', 'Last Payment',
            ]
            return self.export_as_excel(request, excel_data, headers)

        # Fix: set object_list so get_context_data works
        self.object_list = customers_qs
        context = self.get_context_data()
        context.update({
            'form': CustomerForm(),
            'customers': enriched_customers,
            'status': status_filter,
            'plan': plan_filter,
            'search': search_query,
        })
        return self.render_to_response(context)

class UpdateCustomerView(LoginRequiredMixin, View):
    login_url = reverse_lazy('dashboard:admin_login')
    template_name = 'dashboard/Customer-Management.html'

    def _quantize(self, value):
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    from decimal import Decimal, ROUND_HALF_UP

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Get active subscriptions
            active_subs = customer.subscriptions.filter(is_active=True).select_related('plan')

            # Calculate due amount and revised amount using the same logic as CustomerDataMixin
            due_amount = Decimal("0.00")
            revised_amount_total = Decimal("0.00")
            base_plan_id = None
            addon_plan_ids = []
            start_date = None

            for sub in active_subs:
                # Use revised amount if present, else plan price
                if sub.revised_amount is not None and sub.revised_amount > 0:
                    amount = Decimal(sub.revised_amount)
                else:
                    amount = Decimal(sub.plan.price)

                due_amount += amount
                revised_amount_total += Decimal(sub.revised_amount or 0)

                if sub.plan.plan_type == 'base':
                    base_plan_id = sub.plan.id
                    start_date = sub.start_date
                elif sub.plan.plan_type == 'add_on':
                    addon_plan_ids.append(sub.plan.id)

            # Plan options
            base_plans = list(Plan.objects.filter(plan_type='base').values('id', 'name', 'price'))
            addon_plans = list(Plan.objects.filter(plan_type='add_on').values('id', 'name', 'price'))

            data = {
                'name': customer.name,
                'mobile': customer.mobile,
                'email': customer.email,
                'address': customer.address,
                'base_plan_id': base_plan_id,
                'addon_plan_ids': addon_plan_ids,
                'due_amount': f"{due_amount:.2f}",
                'revised_amount': f"{revised_amount_total:.2f}",
                'start_date': start_date.isoformat() if start_date else '',
                'base_plans': base_plans,
                'add_on_plans': addon_plans
            }
            return JsonResponse(data)

        return redirect('dashboard:customer_list')

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        form = CustomerForm(request.POST, instance=customer)

        if form.is_valid():
            customer = form.save()
            base_plan = form.cleaned_data.get('base_plan')
            addon_plans = form.cleaned_data.get('add_on_plan')
            revised_amount_total = Decimal(form.cleaned_data.get('revised_amount') or 0)
            start_date = form.cleaned_data.get('start_date') or date.today()

            # Collect all plans first
            plans = []
            if base_plan:
                plans.append(base_plan)
            if addon_plans:
                plans.extend(addon_plans)

            plan_count = len(plans)
            revised_per_plan = (
                (revised_amount_total / plan_count) if plan_count > 0 else Decimal("0.00")
            )

            # Clear existing subscriptions
            Subscription.objects.filter(customer=customer).delete()

            # Create new subscriptions with split revised amount
            for plan in plans:
                Subscription.objects.create(
                    customer=customer,
                    plan=plan,
                    start_date=start_date,
                    end_date=start_date + timedelta(days=plan.duration_days),
                    revised_amount=revised_per_plan
                )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Customer {customer.customer_id} updated successfully.'
                })

            messages.success(request, f"Customer {customer.customer_id} updated successfully.")
            return redirect('dashboard:customer_list')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })

        messages.error(request, "Failed to update customer.")
        return redirect('dashboard:customer_list')


class CustomerDetailView(LoginRequiredMixin, View):
    template_name = 'dashboard/Customer-Detail.html'

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        today = timezone.now().date()

        # Only active subscriptions
        subs_qs = (Subscription.objects
                   .filter(customer=customer, is_active=True)
                   .select_related('plan'))

        base_plan_sub = (subs_qs
                         .filter(plan__plan_type='base')
                         .order_by('-start_date')
                         .first())

        current_start = base_plan_sub.start_date if base_plan_sub else None

        if current_start:
            add_on_subs = list(
                subs_qs.filter(plan__plan_type='add_on', start_date=current_start)
            )
        else:
            add_on_subs = []

        current_subs = [s for s in [base_plan_sub] + add_on_subs if s]

        assigned_on = current_start
        due_date = assigned_on + relativedelta(months=1) if assigned_on else None

        # --- Due amount & revised amount (same as CustomerDataMixin) ---
        due_amount = Decimal("0.00")
        revised_total = Decimal("0.00")
        has_revised = False
        plan_details = []

        for sub in current_subs:
            if sub.revised_amount is not None and sub.revised_amount > 0:
                amount = Decimal(sub.revised_amount)
                has_revised = True
            else:
                amount = Decimal(sub.plan.price)
            revised_total += amount
            due_amount += Decimal(sub.plan.price)
            plan_details.append(f"{sub.plan.name} (₹{amount:.2f})")

        # If no revised amounts were found, keep revised_total as None
        if not has_revised:
            revised_total = None
            final_amount = due_amount
        else:
            final_amount = revised_total

        # Round all monetary values to 2 decimals
        due_amount = due_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if revised_total is not None:
            revised_total = revised_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        final_amount = final_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        context = {
            'customer': customer,
            'base_plan': base_plan_sub.plan if base_plan_sub and base_plan_sub.plan else None,
            'add_ons': [s.plan for s in add_on_subs if s.plan],
            'assigned_on': assigned_on,
            'due_date': due_date,
            'plan_details': plan_details,
            'due_amount': f"{due_amount:,.2f}",
            'final_amount': f"{final_amount:,.2f}",
        }

        if revised_total is not None:
            context['revised_amount'] = f"{revised_total:,.2f}"

        return render(request, self.template_name, context)

class ToggleCustomerStatusView(LoginRequiredMixin, View):
    login_url = reverse_lazy('dashboard:admin_login')

    @method_decorator(require_POST)
    def post(self, request, pk):
        customer = Customer.objects.filter(pk=pk).first()

        if not customer:
            messages.error(request, "Customer not found.")
            return redirect('dashboard:customer_list')

        if customer.status == 'active':
            customer.soft_delete()
            messages.success(request, f"Customer {customer.name} deactivated successfully.")
        else:
            customer.activate()
            messages.success(request, f"Customer {customer.name} activated successfully.")

        return redirect('dashboard:customer_list')

@method_decorator(csrf_exempt, name='dispatch')
class CheckCustomerDuplicatesView(View):

    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip().lower()
            mobile = data.get('mobile', '').strip()

            return JsonResponse({
                "email_exists": Customer.objects.filter(email__iexact=email).exists(),
                "mobile_exists": Customer.objects.filter(mobile=mobile).exists()
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
class RazorpayPaymentView(View):
    def get(self, request, customer_id):
        customer = get_object_or_404(Customer, customer_id=customer_id)
        today = now().date()
        active_subscriptions = customer.subscriptions.filter(end_date__gte=today)

        # 1. Calculate total due for current cycle
        cycle_due = sum(
            sub.revised_amount if sub.revised_amount is not None else sub.plan.price
            for sub in active_subscriptions
        )

        # 2. Get total payments already made in this billing cycle
        cycle_start = today.replace(day=1)   # first day of current month
        cycle_end = (cycle_start + relativedelta(months=1)) - timedelta(days=1)

        total_paid = Payment.objects.filter(
            customer=customer,
            payment_date__date__gte=cycle_start,
            payment_date__date__lte=cycle_end,
            status="success"
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal(0)

        # 3. Remaining due
        remaining_due = cycle_due - total_paid

        # ✅ Round small floating point errors
        if remaining_due < Decimal("0.01"):
            remaining_due = Decimal("0.00")

        if remaining_due <= 0:
            # All dues cleared
            return render(request, "payments/No-Dues.html", {
                "customer": customer,
                "message": "You have no pending dues!"
            })

        # 4. Proceed with Razorpay order for remaining due
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            order_data = {
                "amount": int(remaining_due * 100),  # convert to paise
                "currency": "INR",
                "payment_capture": "1"
            }

            payment_order = client.order.create(order_data)
            if not payment_order.get("id"):
                raise Exception("Failed to create Razorpay order")

        except Exception as e:
            return render(request, "payments/Unsuccesfull.html", {
                "error": f"Payment system error: {str(e)}",
                "customer": customer,
                "display_amount": remaining_due,
                "active_subscriptions": active_subscriptions
            })

        context = {
            "razorpay_order_id": payment_order["id"],
            "amount_paise": int(remaining_due * 100),
            "display_amount": remaining_due,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "customer": customer,
            "customer_id": customer.customer_id,
            "callback_url": request.build_absolute_uri(reverse("dashboard:razorpay-verify")),
            "active_subscriptions": active_subscriptions,
        }

        return render(request, "payments/razorpay_checkout.html", context)

# class RazorpayPaymentView(View):
#     def get(self, request, customer_id):
#         customer = get_object_or_404(Customer, customer_id=customer_id)
#         today = now().date()
#         active_subscriptions = customer.subscriptions.filter(end_date__gte=today)
#         last_payment = Payment.objects.filter(customer=customer).order_by('-payment_date').first()
#
#         if last_payment:
#             payment_date = last_payment.payment_date.date()
#             next_due_date = payment_date + relativedelta(months=1)
#
#             if today < next_due_date:
#                 return render(request, "payments/No-Dues.html", {
#                     "customer": customer,
#                     "payment": last_payment,
#                     "next_due_date": next_due_date,
#                     "payment_method": last_payment.payment_method,
#                     "plan": active_subscriptions.first().plan if active_subscriptions.exists() else None
#                 })
#
#         # due_amount = sum(sub.plan.price for sub in active_subscriptions)
#         due_amount = sum(
#             sub.revised_amount if sub.revised_amount is not None else sub.plan.price
#             for sub in active_subscriptions
#         )
#
#         # If no dues, redirect to No-Dues page
#         if due_amount <= 0:
#             return render(request, "payments/No-Dues.html", {
#                 "customer": customer,
#                 "message": "You have no pending dues!"
#             })
#
#         # Create Razorpay order
#         try:
#             client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
#
#             order_data = {
#                 "amount": int(due_amount * 100),  # in paise
#                 "currency": "INR",
#                 "payment_capture": "1"  # Auto-capture payment
#             }
#
#             payment_order = client.order.create(order_data)
#
#             # Verify the order was created properly
#             if not payment_order.get("id"):
#                 raise Exception("Failed to create Razorpay order")
#
#
#         except Exception as e:
#             return render(request, "payments/Unsuccesfull.html", {
#                 "error": f"Payment system error: {str(e)}",
#                 "customer": customer,
#                 "display_amount": due_amount,
#                 "active_subscriptions": active_subscriptions
#             })
#
#         # Pass to template
#         context = {
#             "razorpay_order_id": payment_order["id"],
#             "amount_paise": int(due_amount * 100),
#             "display_amount": due_amount,
#             "razorpay_key_id": settings.RAZORPAY_KEY_ID,
#             "customer": customer,
#             "customer_id": customer.customer_id,
#             "callback_url": request.build_absolute_uri(reverse("dashboard:razorpay-verify")),
#             "active_subscriptions": active_subscriptions,
#         }
#
#         for key, value in context.items():
#             if key == "razorpay_key_id":
#                 print(f"{key}: {str(value)[:10]}...")
#             else:
#                 print(f"{key}: {value}")
#
#         return render(request, "payments/razorpay_checkout.html", context)

@method_decorator(csrf_exempt, name='dispatch')
class RazorpayVerifyPaymentView(View):
    def post(self, request):
        import json
        from decimal import Decimal
        from dateutil.relativedelta import relativedelta

        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"status": "fail", "message": "Invalid JSON"}, status=400)

        required_fields = ["razorpay_order_id", "customer_id"]
        missing_fields = [f for f in required_fields if f not in data or not data[f]]
        if missing_fields:
            return JsonResponse({"status": "fail", "message": f"Missing fields: {', '.join(missing_fields)}"}, status=400)

        # Get customer
        try:
            customer = Customer.objects.get(customer_id=data["customer_id"])
        except Customer.DoesNotExist:
            return JsonResponse({"status": "fail", "message": "Customer not found"}, status=404)

        # Get or create Payment record for this order
        payment, created = Payment.objects.get_or_create(
            razorpay_order_id=data["razorpay_order_id"],
            defaults={
                "customer": customer,
                "amount": Decimal("0.00"),  # Will update later if needed
                "status": "initiated",
                "payment_method": "Razorpay"
            }
        )

        # If Razorpay payment ID is missing → Payment failed or abandoned
        if not data.get("razorpay_payment_id") or not data.get("razorpay_signature"):
            payment.status = "failed"
            payment.notes = "Payment failed or cancelled by user"
            payment.save(update_fields=["status", "notes", "updated_at"])
            return JsonResponse({"status": "fail", "message": "Payment failed"}, status=400)

        # Verify payment signature
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": data["razorpay_order_id"],
                "razorpay_payment_id": data["razorpay_payment_id"],
                "razorpay_signature": data["razorpay_signature"]
            })
        except Exception:
            payment.status = "failed"
            payment.notes = "Signature verification failed"
            payment.save(update_fields=["status", "notes", "updated_at"])
            return JsonResponse({"status": "fail", "message": "Verification failed"}, status=400)

        # At this point payment is successful
        today = now().date()
        active_subscriptions = customer.subscriptions.filter(end_date__gte=today)
        # amount = sum(Decimal(sub.plan.price) for sub in active_subscriptions)
        amount = sum(
            Decimal(sub.revised_amount) if sub.revised_amount is not None else Decimal(sub.plan.price)
            for sub in active_subscriptions
        )
        # Build subscription snapshot
        subscription_snapshot = []
        for sub in active_subscriptions:
            subscription_snapshot.append({
                "plan_id": sub.plan.id,
                "plan_name": sub.plan.name,
                "original_price": str(sub.plan.price),
                "revised_amount": str(sub.revised_amount) if sub.revised_amount else None,
                "start_date": sub.start_date.strftime("%Y-%m-%d"),
                "end_date": sub.end_date.strftime("%Y-%m-%d"),
            })

        payment.amount = amount
        payment.payment_date = today
        payment.payment_for_month = today
        payment.upi_transaction_id = data["razorpay_payment_id"]
        payment.razorpay_signature = data["razorpay_signature"]
        payment.status = "success"
        payment.notes = f"Payment for {active_subscriptions.count()} subscriptions"
        payment.snapshot = subscription_snapshot
        payment.save()

        payment.subscriptions.set(active_subscriptions)
        next_due_date = today + relativedelta(months=1)

        return JsonResponse({
            "status": "success",
            "message": "Payment verified successfully",
            "payment_id": payment.id,
            "amount": float(amount),
            "next_due_date": next_due_date.strftime("%Y-%m-%d")
        })

class PaymentReceiptView(View):
    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)
        return render(request, "payments/receipt.html", {
            "payment": payment,
            "customer": payment.customer,
            "subscriptions": payment.subscriptions.all()
        })


class PaymentReceiptPDFView(View):
    def get(self, request, payment_id):
        # Fetch payment object
        payment = get_object_or_404(Payment, id=payment_id)

        # Prepare HTTP response for PDF download
        filename = f"Receipt_{payment.customer.customer_id}_{payment.id}.pdf"
        response = HttpResponse(content_type="application/pdf")
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Create PDF
        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        y = height - inch

        # ===== HEADER =====
        p.setFont("Helvetica-Bold", 18)
        p.drawCentredString(width / 2.0, y, "PAYMENT RECEIPT")
        y -= 30

        p.setFont("Helvetica", 10)
        p.drawCentredString(width / 2.0, y, f"Generated on: {datetime.now().strftime('%b %d, %Y')}")
        y -= 40

        # ===== CUSTOMER DETAILS =====
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Customer Information")
        y -= 15
        p.setFont("Helvetica", 11)
        p.drawString(50, y, f"Customer ID: {payment.customer.customer_id}")
        y -= 15
        p.drawString(50, y, f"Name: {payment.customer.name}")
        y -= 30

        # ===== PAYMENT DETAILS =====
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Payment Information")
        y -= 15
        p.setFont("Helvetica", 11)
        # p.drawString(50, y, f"Payment Date: {payment.payment_date.strftime('%b %d, %Y')}")
        y -= 15
        p.drawString(50, y, f"Amount Paid:{payment.amount}")
        y -= 15
        p.drawString(50, y, f"Payment Method: {payment.payment_method}")
        y -= 15
        p.drawString(50, y, f"Transaction ID: {payment.upi_transaction_id}")
        y -= 30

        # ===== SUBSCRIBED PLANS TABLE =====
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Subscribed Plans")
        y -= 20

        data = [["Plan Name", "Price", "Start Date", "End Date"]]
        for sub in payment.subscriptions.all():
            data.append([
                sub.plan.name,
                f"{sub.plan.price}",
                sub.start_date.strftime('%b %d, %Y'),
                sub.end_date.strftime('%b %d, %Y')
            ])

        table = Table(data, colWidths=[150, 100, 120, 120])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        table.wrapOn(p, width, height)
        table.drawOn(p, 50, y - (len(data) * 18))
        y -= (len(data) * 18) + 40

        # ===== FOOTER =====
        p.setFont("Helvetica-Oblique", 11)
        p.drawString(50, y, "Thank you for your payment. Please keep this receipt for your records.")

        # Save PDF
        p.showPage()
        p.save()

        return response

class PaymentSuccessView(View):
    """View to handle successful payment display"""

    def get(self, request):
        payment_id = request.GET.get('payment_id')

        if not payment_id:
            # If no payment ID, redirect to dashboard
            return redirect('dashboard:customer_list')
        try:
            payment = Payment.objects.get(id=payment_id)
            # Calculate next due date
            next_due_date = payment.payment_date + relativedelta(months=1)
            context = {
                'payment': payment,
                'payment_method': payment.payment_method,
                'next_due_date': next_due_date,
            }
            return render(request, 'payments/Payment-success.html', context)
        except Payment.DoesNotExist:
            return redirect('dashboard:customer_list')

class PaymentFailedView(View):
    """View to handle failed payment display"""

    def get(self, request):
        error_message = request.GET.get('error', 'Payment failed. Please try again.')
        customer_id = request.GET.get('customer_id')
        context = {
            'error_message': error_message,
            'customer_id': customer_id,
        }
        if customer_id:
            try:
                customer = Customer.objects.get(customer_id=customer_id)
                today = now().date()
                active_subscriptions = customer.subscriptions.filter(end_date__gte=today)
                due_amount = sum(sub.plan.price for sub in active_subscriptions)

                context.update({
                    'customer': customer,
                    'display_amount': due_amount,
                    'active_subscriptions': active_subscriptions,
                })
            except Customer.DoesNotExist:
                pass
        return render(request, 'payments/Unsuccesfull.html', context)

