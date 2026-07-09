from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    first_name = serializers.ReadOnlyField(source='user.first_name')
    last_name = serializers.ReadOnlyField(source='user.last_name')
    email = serializers.ReadOnlyField(source='user.email')
    team_name = serializers.ReadOnlyField(source='team.name')

    class Meta:
        model = UserProfile
        fields = ['id', 'user_id', 'username', 'first_name', 'last_name', 'email', 'role', 'team', 'team_name']
