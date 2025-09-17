from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import requests
import logging
from django.utils import timezone
from django.core.management.base import BaseCommand


logger = logging.getLogger(__name__)

class SubscriptionNotificationManager:
    def __init__(self, subscription):
        self.subscription = subscription
        self.company = subscription.company
        
    def send_email_notification(self):
        """Send email notifications to company admins"""
        context = self._get_notification_context()
        
        # Get company-specific recipients
        recipients = self._get_notification_recipients()
        
        if recipients:
            try:
                send_mail(
                    subject=f"Subscription Expiring Soon - {self.company.name}",
                    message=render_to_string('company/emails/subscription_expiring.txt', context),
                    html_message=render_to_string('company/emails/subscription_expiring.html', context),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipients
                )
                logger.info(f"Sent expiry notification to {self.company.name}")
                return True
            except Exception as e:
                logger.error(f"Failed to send email to {self.company.name}: {str(e)}")
                return False
    
    def send_slack_notification(self):
        """Send Slack notification if company has enabled it"""
        if self.company.notify_slack and self.company.slack_webhook_url:
            try:
                context = self._get_notification_context()
                slack_message = {
                    "text": self._format_slack_message(context)
                }
                response = requests.post(self.company.slack_webhook_url, json=slack_message)
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Slack notification failed for {self.company.name}: {str(e)}")
                return False
    
    def _get_notification_recipients(self):
        """Get company-specific notification recipients"""
        recipients = set()
        
        # Add company notification email if set
        if self.company.notification_email:
            recipients.add(self.company.notification_email)
        
        # Add active company admins
        admin_emails = self.company.users.filter(
            is_active=True,
            is_staff=True
        ).values_list('email', flat=True)
        recipients.update(admin_emails)
        
        return list(recipients)
    
    def _get_notification_context(self):
        """Get context for notification templates"""
        return {
            'company_name': self.company.name,
            'end_date': self.subscription.end_date,
            'days_left': (self.subscription.end_date - timezone.now()).days,
            'renewal_url': f"{settings.BASE_URL}/subscriptions/{self.subscription.id}/renew/",
            'plan_name': self.subscription.plan.name
        }
    


