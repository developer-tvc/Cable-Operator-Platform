from django.db import models
from apps.accounts.models import Customer
from django.utils import timezone

class QRCode(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
    ]

    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='qr_code')
    image = models.ImageField(upload_to='qr_codes/')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"QR for {self.customer.customer_id} - {self.status}"

class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    customer = models.ForeignKey('accounts.Customer', on_delete=models.CASCADE, related_name='payments')
    plan = models.ForeignKey('plans.Plan', on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_for_month = models.DateField(help_text="The month this payment is for")
    upi_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='initiated')
    receipt_file = models.FileField(upload_to='receipts/', blank=True, null=True)

    def __str__(self):
        return f"{self.customer.name} - ₹{self.amount} - {self.status}"

    class Meta:
        ordering = ['-payment_date']
