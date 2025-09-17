from django.core.management.base import BaseCommand
from django.utils import timezone
from company.models import Subscription

class Command(BaseCommand):
    help = 'Send notifications for expiring subscriptions'

    def handle(self, *args, **options):
        today = timezone.now()
        expiring_subscriptions = Subscription.objects.filter(
            status='active',
            end_date__gt=today,
            end_date__lte=today + timezone.timedelta(days=7)
        )
        
        notification_count = 0
        for subscription in expiring_subscriptions:
            if subscription.notify_expiring_soon():
                notification_count += 1
                
        self.stdout.write(
            self.style.SUCCESS(f'Sent {notification_count} expiry notifications')
        )