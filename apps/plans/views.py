from django.shortcuts import render, redirect, get_object_or_404
from .models import Plan
from .forms import PlanForm
from django.http import HttpResponse
from django.views import View
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.conf import settings
import os
from apps.accounts.models import Customer
from reportlab.lib.units import inch


def plan_list(request):
    plans = Plan.objects.all()
    return render(request, 'plans/plan_list.html', {'plans': plans})

def create_plan(request):
    if request.method == 'POST':
        form = PlanForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('plan_list')
    else:
        form = PlanForm()
    return render(request, 'plans/create_plan.html', {'form': form})

def update_plan(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    if request.method == 'POST':
        form = PlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            return redirect('plan_list')
    else:
        form = PlanForm(instance=plan)
    return render(request, 'plans/update_plan.html', {'form': form, 'plan': plan})

def delete_plan(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    if request.method == 'POST':
        plan.delete()
        return redirect('plan_list')
    return render(request, 'plans/delete_plan.html', {'plan': plan})


class DownloadQRCodePDFView(View):
    def get(self, request, customer_id):
        customer = get_object_or_404(Customer, pk=customer_id)

        if not customer.qr_code or not customer.qr_code.image:
            return HttpResponse("QR Code not found.", status=404)

        # Setup response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{customer.customer_id}_qr.pdf"'

        # A4 canvas
        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4

        # Path to QR code image
        qr_path = os.path.join(settings.MEDIA_ROOT, customer.qr_code.image.name)

        if os.path.exists(qr_path):
            # Increase QR code size to ~4 inches (288 pts)
            qr_size = 4 * inch
            x = (width - qr_size) / 2
            y = (height + qr_size) / 2  # So image is vertically centered

            p.drawImage(qr_path, x, y - qr_size, width=qr_size, height=qr_size)

            # Draw customer info just below the QR
            text_y = y - qr_size - 40
            p.setFont("Helvetica-Bold", 14)
            p.drawCentredString(width / 2, text_y, f"Customer ID: {customer.customer_id}")
            text_y -= 20
            p.setFont("Helvetica", 12)
            p.drawCentredString(width / 2, text_y, f"Name: {customer.name}")
            # text_y -= 20
            # p.drawCentredString(width / 2, text_y, f"Address: {customer.address}")
        else:
            p.drawString(100, 750, "QR image file not found.")

        p.showPage()
        p.save()
        return response