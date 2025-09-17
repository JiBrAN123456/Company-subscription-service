from django.core import mail
from django.test import TestCase
from django.conf import settings

class NotificationTest(TestCase):
    def test_email_configuration(self):
        mail.send_mail(
            'Test Subject',
            'Test Message',
            settings.DEFAULT_FROM_EMAIL,
            ['test@example.com'],
            fail_silently=False,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Test Subject')