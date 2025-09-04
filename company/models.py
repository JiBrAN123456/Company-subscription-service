from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError


class Company(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "companies"
        ordering = ["name"]
        verbose_name_plural = "Companies"
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    def suspend(self):
        """Suspend company and all its users"""
        self.status = "suspended"
        self.save()
        # Suspend all users under this company
        self.users.update(is_active=False)
    
    def activate(self):
        """Activate company (users need to be activated separately if needed)"""
        self.status = "active"
        self.save()
    
    @property
    def active_subscription(self):
        """Get the company's active subscription"""
        return self.subscriptions.filter(status='active').first()
    
    @property
    def can_add_users(self):
        """Check if company can add more users based on subscription"""
        active_sub = self.active_subscription
        if not active_sub:
            return False
        
        if active_sub.plan.pricing_model == 'per_user' and active_sub.max_users:
            current_user_count = self.users.filter(is_active=True).count()
            return current_user_count < active_sub.max_users
        
        return True


class SubscriptionPlan(models.Model):
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    PRICING_MODEL_CHOICES = [
        ('flat_fee', 'Flat Fee'),
        ('per_user', 'Per User'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES)
    pricing_model = models.CharField(max_length=20, choices=PRICING_MODEL_CHOICES)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    user_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Max users for per-user plans")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "subscription_plans"
        ordering = ["name"]
    
    def __str__(self):
        return f"{self.name} - {self.get_billing_cycle_display()} ({self.get_pricing_model_display()})"
    
    def clean(self):
        """Validate that per-user plans have user limits"""
        if self.pricing_model == 'per_user' and not self.user_limit:
            raise ValidationError("Per-user plans must have a user limit specified")


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
    
    # Snapshot fields from plan at creation
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
        if not self.end_date and self.start_date and self.plan:
            if self.plan.billing_cycle == "monthly":
                self.end_date = self.start_date + relativedelta(months=1)
            elif self.plan.billing_cycle == "quarterly":
                self.end_date = self.start_date + relativedelta(months=3)
            elif self.plan.billing_cycle == "yearly":
                self.end_date = self.start_date + relativedelta(years=1)
        
        # Snapshot important values from plan
        if self.plan and not self.max_users:
            self.max_users = self.plan.user_limit
        if self.plan and not self.cost_at_signup:
            self.cost_at_signup = self.plan.cost
        
        super().save(*args, **kwargs)
        
        # If subscription becomes inactive, suspend company users
        if self.status in ['expired', 'suspended']:
            self.company.users.update(is_active=False)
    
    def is_active(self):
        """Check if subscription is currently active"""
        return (
            self.status == "active" and 
            self.end_date and 
            self.end_date > timezone.now()
        )
    
    def suspend(self):
        """Suspend subscription and company users"""
        self.status = 'suspended'
        self.save()
    
    def expire(self):
        """Mark subscription as expired"""
        self.status = 'expired'
        self.save()


class User(AbstractUser):
    company = models.ForeignKey("company.Company", on_delete=models.CASCADE, related_name="users")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "users"
        ordering = ["username"]
    
    def clean(self):
        """Validate user creation against company subscription limits"""
        if self.company_id:
            company = Company.objects.get(id=self.company_id)
            if not company.can_add_users:
                active_sub = company.active_subscription
                if active_sub and active_sub.plan.pricing_model == 'per_user':
                    raise ValidationError(
                        f"Cannot add user. Company has reached the maximum limit of {active_sub.max_users} users."
                    )
                else:
                    raise ValidationError("Cannot add user. Company has no active subscription.")
    
    def save(self, *args, **kwargs):
        # Validate before saving
        self.clean()
        
        # Ensure user is inactive if company subscription is not active
        if self.company:
            active_sub = self.company.active_subscription
            if not active_sub or not active_sub.is_active():
                self.is_active = False
        
        super().save(*args, **kwargs)


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('cash', 'Cash'),
        ('other', 'Other'),
    ]
    
    subscription = models.ForeignKey("Subscription", on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "payments"
        ordering = ["-payment_date"]
    
    def __str__(self):
        return f"Payment {self.id} - {self.subscription.company.name} - ${self.amount}"