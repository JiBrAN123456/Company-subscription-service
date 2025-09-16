from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from company.models import Company, SubscriptionPlan, Subscription

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