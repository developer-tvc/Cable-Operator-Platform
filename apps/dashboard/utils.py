import qrcode
from django.core.files import File
from io import BytesIO
from django.urls import reverse
from apps.payments.models import QRCode

def generate_customer_qr(customer, request):
    relative_url = reverse('dashboard:gpay_redirect', args=[customer.customer_id])

    full_url = request.build_absolute_uri(relative_url)

    qr_image = qrcode.make(full_url)
    buffer = BytesIO()
    qr_image.save(buffer, format="PNG")
    buffer.seek(0)

    qr_model = QRCode.objects.create(
        customer=customer,
        status='active'
    )
    qr_model.image.save(f"{customer.customer_id}.png", File(buffer), save=True)
    return qr_model
