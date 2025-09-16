from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from .models import Company, SubscriptionPlan, Subscription, Payment



User = get_user_model()

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'status', 'created_at', 'updated_at',
            'notification_email', 'notify_slack', 'slack_webhook_url',
            'notification_days_before'
        ]

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'billing_cycle', 'pricing_model',
            'cost', 'user_limit', 'is_active', 'created_at', 
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        # Validate billing cycle
        valid_billing_cycles = ['monthly', 'yearly']  # Update these based on your model choices
        if 'billing_cycle' in data and data['billing_cycle'] not in valid_billing_cycles:
            raise serializers.ValidationError({
                'billing_cycle': f"Must be one of: {', '.join(valid_billing_cycles)}"
            })

        # Validate pricing model
        valid_pricing_models = ['per_user', 'flat_rate']  # Update these based on your model choices
        if 'pricing_model' in data and data['pricing_model'] not in valid_pricing_models:
            raise serializers.ValidationError({
                'pricing_model': f"Must be one of: {', '.join(valid_pricing_models)}"
            })

        # Validate cost is positive
        if 'cost' in data and float(data['cost']) <= 0:
            raise serializers.ValidationError({
                'cost': "Cost must be greater than 0"
            })

        # Validate user limit is positive
        if 'user_limit' in data and data['user_limit'] <= 0:
            raise serializers.ValidationError({
                'user_limit': "User limit must be greater than 0"
            })

        return data






class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'email', 'first_name', 'last_name'
                  'company', 'is_active']
        read_only_fields = ['is_active']

        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
           user.set_password(password)
           user.save()
        return user





class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            'id', 'company', 'plan', 'status',
            'start_date', 'end_date', 'max_users',
            'cost_at_signup', 'created_at', 'updated_at'
        ]
    
    def validate(self, data):

        company = data.get('company')
        if company and company.active_subscription:
            raise serializers.ValidationError("Company already has an active subscription.")        
        
        return data
    
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

    def validate(self, data):

        subscription = data.get('subscription')
        amount = data.get("amount")

        if subscription and amount:
            if amount > subscription.cost_at_signup:
                raise serializers.ValidationError("Payment amount exceeds subscription cost.")

        return data    


class CompanyDetailSerializer(CompanySerializer):
    active_subscription = SubscriptionSerializer(read_only=True)
    users = UserSerializer(many=True, read_only=True)

    class Meta(CompanySerializer.Meta):
        fields = CompanySerializer.Meta.fields + ['active_subscription', 'users']

class SubscriptionDetailSerializer(SubscriptionSerializer):
    company = CompanySerializer(read_only=True)
    plan = SubscriptionPlanSerializer(read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta(SubscriptionSerializer.Meta):
        fields = SubscriptionSerializer.Meta.fields + ['payments']