from dateutil.relativedelta import relativedelta
from django.db.models import Count, Q, Prefetch
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from calendar import monthrange
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from datetime import date, timedelta
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
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
import razorpay
import json
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal,ROUND_HALF_UP
from django.utils import timezone

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
#
#         for customer in customers:
#             # Safely fallback if latest_subscriptions not present
#             subscriptions = getattr(customer, 'latest_subscriptions', customer.subscriptions.all())
#             latest_sub = next(iter(subscriptions), None)
#
#             plan_details = (
#                 f"{latest_sub.plan.name} - ₹{latest_sub.plan.price}"
#                 if latest_sub and latest_sub.plan else "No Plan"
#             )
#             due_amount = latest_sub.plan.price if latest_sub and latest_sub.plan else 0
#             last_payment = Payment.objects.filter(customer=customer, status='success').order_by('-payment_date').first()
#             last_payment_display = (
#                 last_payment.payment_date.strftime('%d-%b-%Y')
#                 if last_payment and last_payment.payment_date else 'N/A'
#             )
#
#             customer_data.append({
#                 'id': customer.id,
#                 'customer_id': customer.customer_id,
#                 'name': customer.name,
#                 'mobile': customer.mobile,
#                 'status': customer.status,
#                 'plan_details': plan_details,
#                 'due_amount': due_amount,
#                 'last_payment': last_payment_display,
#             })
#
#         return customer_data

class CustomerDataMixin:
    def get_enriched_customer_data(self, customers):
        customer_data = []

        for customer in customers:
            # All active plans (base + add-ons)
            active_subs = customer.subscriptions.filter(is_active=True).select_related('plan')
            plan_list = [
                f"{sub.plan.name} (₹{sub.revised_amount if sub.revised_amount is not None else sub.plan.price})"
                for sub in active_subs if sub.plan
            ]

            # Total revised amount from active subscriptions
            # total_revised_amount = sum(sub.revised_amount for sub in active_subs if sub.revised_amount)
            # Use revised_amount if available; otherwise fallback to original plan price
            total_revised_amount = sum(
                sub.revised_amount if sub.revised_amount is not None else sub.plan.price
                for sub in active_subs if sub.plan
            )

            # Fallback for latest subscription if needed
            latest_sub = next(iter(getattr(customer, 'latest_subscriptions', [])), None)

            # Fallback to single plan details if needed
            plan_details = (
                f"{latest_sub.plan.name} - ₹{latest_sub.plan.price}"
                if latest_sub and latest_sub.plan else "No Plan"
            )

            # Due amount: can use total revised amount instead
            due_amount = total_revised_amount

            # Last successful payment
            last_payment = Payment.objects.filter(customer=customer, status='success')\
                                          .order_by('-payment_date').first()
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
                'due_amount': due_amount,
                'last_payment': last_payment_display,
                'total_revised_amount': total_revised_amount,
                'qr_code_url': customer.qr_code.image.url if hasattr(customer, 'qr_code') and customer.qr_code and customer.qr_code.image else None,
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

                    if isinstance(cell_value, list):
                        cell_value = ', '.join(map(str, cell_value))

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
                ", ".join(c['plan_details']),
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
                    revised_plan_amount = (revised_amount * proportion).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                else:
                    revised_plan_amount = original_price

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

class RazorpayPaymentView(View):
    def get(self, request, customer_id):
        customer = get_object_or_404(Customer, customer_id=customer_id)
        today = now().date()
        active_subscriptions = customer.subscriptions.filter(end_date__gte=today)

        due_amount = sum(sub.plan.price for sub in active_subscriptions)
        if due_amount <= 0:
            return render(request, "payments/no_dues.html", {"customer": customer})

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment_order = client.order.create(dict(
            amount=int(due_amount * 100),  # Razorpay uses paise
            currency='INR',
            payment_capture='1'
        ))

        context = {
            "customer": customer,
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "order_id": payment_order['id'],
            "amount": due_amount,
            "currency": "INR",
            "callback_url": request.build_absolute_uri("/payments/verify/"),
        }
        return render(request, "payments/razorpay_checkout.html", context)

@method_decorator(csrf_exempt, name='dispatch')
class RazorpayVerifyPaymentView(View):
    def post(self, request):
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            data = {
                "razorpay_order_id": request.POST["razorpay_order_id"],
                "razorpay_payment_id": request.POST["razorpay_payment_id"],
                "razorpay_signature": request.POST["razorpay_signature"]
            }

            client.utility.verify_payment_signature(data)

            customer = Customer.objects.get(customer_id=request.POST["customer_id"])
            amount = 0
            today = now().date()
            for sub in customer.subscriptions.filter(end_date__gte=today):
                amount += sub.plan.price

            payment = Payment.objects.create(
                customer=customer,
                amount=amount,
                payment_date=today,
                payment_method="Razorpay",
                upi_transaction_id=request.POST["razorpay_payment_id"]
            )

            return render(request, "payments/payment-success.html", {
                "payment": payment,
                "payment_method": "Razorpay",
                "next_due_date": today.replace(month=today.month + 1)  # example logic
            })

        except Exception as e:
            return render(request, "payments/unsuccessfull.html", {
                "payment": None,
                "payment_method": "Razorpay"
            })

class UpdateCustomerView(LoginRequiredMixin, View):
    login_url = reverse_lazy('dashboard:admin_login')
    template_name = 'dashboard/Customer-Management.html'

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            latest_sub = Subscription.objects.filter(customer=customer).order_by('-start_date').first()
            due_amount = latest_sub.plan.price if latest_sub and latest_sub.plan else 0
            revised_amount = latest_sub.revised_amount if latest_sub and hasattr(latest_sub, 'revised_amount') else 0

            # Base plan ID from the latest subscription if it's a base
            base_plan_id = latest_sub.plan.id if latest_sub and latest_sub.plan.plan_type == 'base' else None

            # Add-on plans from the same start_date as latest_sub
            addon_plan_ids = []
            if latest_sub:
                addon_plan_ids = list(
                    Subscription.objects.filter(
                        customer=customer,
                        plan__plan_type='add_on',
                        start_date=latest_sub.start_date
                    ).values_list('plan_id', flat=True).distinct()
                )

            start_date = latest_sub.start_date if latest_sub else None

            base_plans = list(Plan.objects.filter(plan_type='base').values('id', 'name', 'price'))
            addon_plans = list(Plan.objects.filter(plan_type='add_on').values('id', 'name', 'price'))

            data = {
                'name': customer.name,
                'mobile': customer.mobile,
                'email': customer.email,
                'address': customer.address,
                'base_plan_id': base_plan_id,
                'addon_plan_ids': addon_plan_ids,
                'due_amount': str(due_amount),
                'revised_amount': str(revised_amount),
                'start_date': start_date.isoformat() if start_date else '',
                'base_plans': base_plans,
                'add_on_plans': addon_plans
            }
            return JsonResponse(data)

        # For normal GET (non-AJAX)
        return redirect('dashboard:customer_list')  # Not used in modal, safe redirect fallback

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        form = CustomerForm(request.POST, instance=customer)

        if form.is_valid():
            customer = form.save()
            base_plan = form.cleaned_data.get('base_plan')
            addon_plans = form.cleaned_data.get('add_on_plan')
            revised_amount = form.cleaned_data.get('revised_amount') or 0
            start_date = form.cleaned_data.get('start_date') or date.today()

            # Clear existing subscriptions
            Subscription.objects.filter(customer=customer).delete()

            # Create new subscriptions
            if base_plan:
                Subscription.objects.create(
                    customer=customer,
                    plan=base_plan,
                    start_date=start_date,
                    end_date=start_date + timedelta(days=base_plan.duration_days),
                    revised_amount=revised_amount
                )

            if addon_plans:
                for addon_plan in addon_plans:
                    Subscription.objects.create(
                        customer=customer,
                        plan=addon_plan,
                         start_date=start_date,
                        end_date=start_date + timedelta(days=addon_plan.duration_days),
                        revised_amount=revised_amount
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
        subscriptions = Subscription.objects.filter(customer=customer)

        base_plan_sub = subscriptions.filter(plan__plan_type='base').first()
        add_on_subs = subscriptions.filter(plan__plan_type='add_on')

        assigned_on = base_plan_sub.start_date if base_plan_sub else None
        due_date = assigned_on + relativedelta(months=1) if assigned_on else None

        due_amount = Decimal('0.00')

        if base_plan_sub:
            base_price = base_plan_sub.revised_amount or base_plan_sub.plan.price
            due_amount += Decimal(base_price)

        for addon_sub in add_on_subs:
            addon_price = addon_sub.revised_amount or addon_sub.plan.price
            due_amount += Decimal(addon_price)

        due_amount = due_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        active_subs = subscriptions.filter(end_date__gte=timezone.now().date())

        total_revised_amount = Decimal('0.00')

        for sub in active_subs:
            total_revised_amount += Decimal(sub.revised_amount or sub.plan.price)

        total_revised_amount = total_revised_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        context = {
            'customer': customer,
            'base_plan': base_plan_sub.plan if base_plan_sub else None,
            'add_ons': [sub.plan for sub in add_on_subs],
            'assigned_on': assigned_on,
            'due_date': due_date,
            'revised_amount': str(total_revised_amount),
            'due_amount': due_amount,
        }
        return render(request, self.template_name, context)


class DeleteCustomerView(LoginRequiredMixin, View):
    login_url = reverse_lazy('dashboard:admin_login')

    @method_decorator(require_POST)
    def post(self, request, pk):
        customer = Customer.objects.filter(pk=pk, status='active').first()
        if customer:
            customer.soft_delete()
            messages.success(request, "Customer deactivated successfully.")
        else:
            messages.error(request, "Customer not found or already inactive.")
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

