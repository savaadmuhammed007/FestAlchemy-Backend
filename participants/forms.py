from django import forms
from django.contrib.auth.models import User
from .models import Team, Member


class TeamLeadRegistrationForm(forms.Form):
    """Creates the team lead user account inline while adding a team."""
    first_name  = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}))
    last_name   = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name (optional)'}))
    username    = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Login username'}))
    password    = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter password'}))

    def clean_username(self):
        uname = self.cleaned_data['username']
        if User.objects.filter(username=uname).exists():
            raise forms.ValidationError("This username is already taken.")
        return uname

    def clean(self):
        cleaned = super().clean()
        pw  = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned

    def save_user(self):
        """Create and return the User (without assigning team yet)."""
        d = self.cleaned_data
        user = User.objects.create_user(
            username   = d['username'],
            password   = d['password'],
            first_name = d['first_name'],
            last_name  = d.get('last_name', ''),
        )
        return user


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'teamlead']
        widgets = {
            'name':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Alpha Team'}),
            'teamlead': forms.Select(attrs={'class': 'form-control'}),
        }


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['name', 'category']
        widgets = {
            'name':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'John Doe'}),
            'category': forms.Select(attrs={'class': 'form-control', 'style': 'background: rgba(0,0,0,0.5);'}),
        }

