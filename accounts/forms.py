from django import forms
from .models import UserProfile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['role', 'team']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control', 'style': 'background: rgba(0,0,0,0.5);'}),
            'team': forms.Select(attrs={'class': 'form-control', 'style': 'background: rgba(0,0,0,0.5);'})
        }
