from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from ..models import Company, SubscriptionPlan, Subscription

class CompanyAPITests(APITestCase):
    def setUp(self):
        self.company_data = {
            'name': 'Test Company',
            'status': 'active',
            'notification_email': 'test@company.com'
        }
        self.company = Company.objects.create(**self.company_data)

    def test_create_company(self):
        url = reverse('company-list')
        data = {
            'name': 'New Company',
            'status': 'active',
            'notification_email': 'new@company.com'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Company.objects.count(), 2)

    def test_suspend_company(self):
        url = reverse('company-suspend', kwargs={'pk': self.company.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.company.refresh_from_db()
        self.assertEqual(self.company.status, 'suspended')

class SubscriptionPlanAPITests(APITestCase):
    def setUp(self):
        self.plan_data = {
            'name': 'Basic Plan',
            'pricing_model': 'per_user',
            'cost': '10.00',
            'user_limit': 5
        }
        self.plan = SubscriptionPlan.objects.create(**self.plan_data)

    def test_list_plans(self):
        url = reverse('subscriptionplan-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)