from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta 
# Create your models here.


class Company(models.Model):   
    STATUS_CHOICES = [
        ('active', 'Active'),
        ("SUSPENDED", "Suspended"),]
     
    name = models.CharField(max_lengh=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active') 

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "companies"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({"self.status"})"
    
    def suspend(self):
        self.status = "SUSPENDED"
        self.save()

    def activate(self):
        self.status = "ACTIVE"
        self.save()    



class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ]

    company = models.ForeignKey("Company", on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey("SubscriptionPlan", on_delete=models.PROTECT, related_name="subscriptions")

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    # snapshot fields from plan at creation
    max_users = models.PositiveIntegerField(null=True, blank=True)
    cost_at_signup = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscriptions"
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company"],
                condition=models.Q(status="active"),
                name="one_active_subscription_per_company"
            )
        ]

    def __str__(self):
        return f"Subscription {self.id} - {self.company.name} ({self.plan.name})"

    def save(self, *args, **kwargs):
        """Auto-calculate end_date and snapshot plan details"""
        if not self.end_date and self.start_date:
            if self.plan.billing_cycle == "monthly":
                self.end_date = self.start_date + relativedelta(months=1)
            elif self.plan.billing_cycle == "quarterly":
                self.end_date = self.start_date + relativedelta(months=3)
            elif self.plan.billing_cycle == "yearly":
                self.end_date = self.start_date + relativedelta(years=1)

        # snapshot important values from plan
        if not self.max_users:
            self.max_users = self.plan.user_limit
        if not self.cost_at_signup:
            self.cost_at_signup = self.plan.cost

        super().save(*args, **kwargs)

    def is_active(self):
        return self.status == "active" and self.end_date > timezone.now()