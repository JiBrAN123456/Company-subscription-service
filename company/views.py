from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Company, SubscriptionPlan, Subscription, Payment , User
from .serializers import (
    CompanySerializer, CompanyDetailSerializer,
    UserSerializer, SubscriptionPlanSerializer,
    SubscriptionSerializer, SubscriptionDetailSerializer,
    PaymentSerializer, UserUpdateSerializer
)
from django.core.exceptions import ValidationError
from django.utils import timezone  
from dateutil.relativedelta import relativedelta 

# Create your views here.

class CompanyViewset(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CompanyDetailSerializer
        return CompanySerializer

    @action(detail=True, methods=['post']) 
    def suspend(self,request, pk = None):
        company = self.get_object()
        company.suspend()
        return Response({"status": "company suspended"}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def activate(self,request,pk = None):
        company = self.get_object()
        company.activate()
        return Response({"status": "company activated"}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def List_active_subscriptions(self):
        company = self.get_object()
        subscription = company.active_subscription
        if not subscription:
            return Response({"detail": "No active subscription found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SubscriptionDetailSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)
     
class SubscriptionPlanViewset(viewsets.ModelViewSet):

    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # Debug output
            print(f"\nValidation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['get'])
    def List_active_subscriptions(self,request, pk=None):
        plan = self.get_object()
        subscriptions = plan.subscriptions.filter(status="active")
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class SubscriptionViewset(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Add validation for company and plan existence
        company_id = serializer.validated_data.get('company').id
        plan_id = serializer.validated_data.get('plan').id
        
        try:
            company = Company.objects.get(id=company_id)
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except (Company.DoesNotExist, SubscriptionPlan.DoesNotExist):
            return Response(
                {"error": "Invalid company or plan ID"},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)




    def get_serializer_class(self):
        if self.action == "retrieve":
            return SubscriptionDetailSerializer
        return SubscriptionSerializer
    

    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        subscription = self.get_object()
        
        try:
            # First, expire any active subscriptions for this company
            Subscription.objects.filter(
                company=subscription.company, 
                status='active'
            ).update(status='expired')

            # Create new subscription
            new_subscription = Subscription.objects.create(
                company=subscription.company,
                plan=subscription.plan,
                status='active',
                start_date=timezone.now(),
                end_date=timezone.now() + relativedelta(months=1) if subscription.plan.billing_cycle == 'monthly' 
                        else timezone.now() + relativedelta(years=1),
                max_users=subscription.max_users,
                cost_at_signup=subscription.plan.cost
            )

            # Reactivate company if needed
            if subscription.company.status == 'suspended':
                subscription.company.activate()

            serializer = self.get_serializer(new_subscription)
            return Response({
                'status': 'subscription renewed',
                'subscription': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Renewal failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=True, methods=['post'])     
    def suspend(self, request, pk=None):
        subscription = self.get_object()
        subscription.suspend()
        return Response({"status": "subscription suspended"}, status=status.HTTP_200_OK)


    def update(self, request, *args, **kwargs):
        subscription = self.get_object()
        serializer = self.get_serializer(subscription, data = request.data , partial = True) 
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentViewset(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate subscription exists and payment amount matches
        subscription_id = serializer.validated_data.get('subscription').id
        try:
            subscription = Subscription.objects.get(id=subscription_id)
            if float(serializer.validated_data.get('amount')) != float(subscription.cost_at_signup):
                return Response(
                    {"error": "Payment amount must match subscription cost"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Subscription.DoesNotExist:
            return Response(
                {"error": "Invalid subscription ID"},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        payment = self.get_object()
       
        try:
            payment.process_payment()
            if payment.status == "completed":
                return Response({"status": "payment processed"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def refund(self,request,pk = None):
        payment = self.get_object()
        try:
            payment.refund()
            if payment.status == "refunded":
                return Response({"status": "payment refunded"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )   
    
    @action(detail=False, methods=['get'])
    def List_payments_for_subscription(self, request):
        subscription_id = request.query.params("subscription_id")
        if not subscription_id:
            return Response(
                {"error": "subscription_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        payments = Payment.objects.filter(subscription_id=subscription_id)
        serializer = self.get_serializer(payments, many = True)
        return Response(serializer.data, status=status.HTTP_200_OK)
          

class UserViewset(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        """Add user for a company"""
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def by_company(self, request):
        """List users for a company"""
        company_id = request.query_params.get("company_id")
        if not company_id:
            return Response({"error": "company_id required"}, status=status.HTTP_400_BAD_REQUEST)
        users = User.objects.filter(company_id=company_id)
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend a user"""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({"status": "user suspended"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a user"""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({"status": "user activated"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def deactivate(self,request,pk = None):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({"message": "user deactivated"}, status=status.Http_200_OK)
    
    @action(detail=True, methods=["post"])
    def update(self, request,*args,**kwargs):
        user = self.get_object()
        serializer = UserUpdateSerializer(user, data=request.data,partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(user).data)

        

