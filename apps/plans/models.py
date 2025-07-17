from django.db import models

class Plan(models.Model):
    PLAN_TYPE_CHOICES = [
        ('base', 'Base Plan'),
        ('add_on', 'Add-On Plan'),
    ]
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.IntegerField(help_text="Duration in days")
    plan_type = models.CharField(max_length=10, choices=PLAN_TYPE_CHOICES)

    def __str__(self):
        return f"{self.name} - ₹{self.price} ({self.plan_type})"