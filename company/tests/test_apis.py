from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from company.models import Company, SubscriptionPlan, Subscription, Payment
from django.utils import timezone
from decimal import Decimal
class CompanyAPITests(APITestCase):
    def setUp(self):
        self.company_data = {
            'name': 'Test Company',
            'status': 'active',
            'notification_email': 'test@company.com',
            'notify_slack': False,
            'slack_webhook_url': None,
            'notification_days_before': 7
        }
        self.company = Company.objects.create(**self.company_data)

    def test_create_company(self):
        url = reverse('company-list')
        data = {
            'name': 'New Company',
            'status': 'active',
            'notification_email': 'new@company.com',
            'notify_slack': False,
            'slack_webhook_url': None,
            'notification_days_before': 7
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Company.objects.count(), 2)
        
    def test_get_company(self):
        url = reverse('company-detail', kwargs={'pk': self.company.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Company')

    def test_suspend_company(self):
        url = reverse('company-suspend', kwargs={'pk': self.company.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.company.refresh_from_db()
        self.assertEqual(self.company.status, 'suspended')


# ...existing code...

class SubscriptionPlanAPITests(APITestCase):
    def setUp(self):
        self.plan_data = {
            'name': 'Basic Plan',
            'billing_cycle': 'monthly',
            'pricing_model': 'per_user',
            'cost': '10.00',
            'user_limit': 5,
            'is_active': True
        }
        self.plan = SubscriptionPlan.objects.create(**self.plan_data)

    def test_create_plan(self):
        url = reverse('subscriptionplan-list')
        data = {
            'name': 'Premium Plan',
            'billing_cycle': 'monthly',
            'pricing_model': 'per_user',
            'cost': '20.00',
            'user_limit': 10,
            'is_active': True
        }
        response = self.client.post(url, data, format='json')
        
        # Debug output
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Data: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SubscriptionPlan.objects.count(), 2)
        
        # Verify the created plan data
        created_plan = SubscriptionPlan.objects.get(name='Premium Plan')
        self.assertEqual(created_plan.billing_cycle, 'monthly')
        self.assertEqual(created_plan.pricing_model, 'per_user')
        self.assertEqual(str(created_plan.cost), '20.00')
        self.assertEqual(created_plan.user_limit, 10)


class SubscriptionWorkflowTests(APITestCase):
    def setUp(self):
        # Create company
        self.company = Company.objects.create(
            name='Test Company',
            status='active',
            notification_email='test@company.com'
        )

        # Create subscription plan
        self.plan = SubscriptionPlan.objects.create(
            name='Basic Plan',
            billing_cycle='monthly',
            pricing_model='per_user',
            cost='99.99',
            user_limit=5,
            is_active=True
        )

    def test_complete_subscription_workflow(self):
        # 1. Create subscription
        sub_url = reverse('subscription-list')
        sub_data = {
            'company': self.company.id,
            'plan': self.plan.id,
            'status': 'active',
            'start_date': timezone.now().date(),
            'max_users': 5,
            'cost_at_signup': '99.99'
        }
        response = self.client.post(sub_url, sub_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        subscription_id = response.data['id']

        # 2. Create payment
        payment_url = reverse('payment-list')
        payment_data = {
            'subscription': subscription_id,
            'amount': '99.99',
            'method': 'credit_card',
            'status': 'pending'
        }
        response = self.client.post(payment_url, payment_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payment_id = response.data['id']

        # 3. Process payment
        process_url = reverse('payment-process', kwargs={'pk': payment_id})
        response = self.client.post(process_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 4. Suspend subscription
        suspend_url = reverse('subscription-suspend', kwargs={'pk': subscription_id})
        response = self.client.post(suspend_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 5. Renew subscription
        renew_url = reverse('subscription-renew', kwargs={'pk': subscription_id})
        response = self.client.post(renew_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class PaymentAPITests(APITestCase):
    def setUp(self):
        # Create necessary objects for payment testing
        self.company = Company.objects.create(name='Test Company')
        self.plan = SubscriptionPlan.objects.create(
            name='Basic Plan',
            cost='99.99',
            billing_cycle='monthly'
        )
        self.subscription = Subscription.objects.create(
            company=self.company,
            plan=self.plan,
            cost_at_signup='99.99'
        )

    def test_payment_lifecycle(self):
        # Create payment
        url = reverse('payment-list')
        data = {
            'subscription': self.subscription.id,
            'amount': '99.99',
            'method': 'credit_card',
            'status': 'pending'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payment_id = response.data['id']

        # Process payment
        process_url = reverse('payment-process', kwargs={'pk': payment_id})
        response = self.client.post(process_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refund payment
        refund_url = reverse('payment-refund', kwargs={'pk': payment_id})
        response = self.client.post(refund_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)