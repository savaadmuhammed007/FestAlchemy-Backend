from django import forms
from django.contrib.auth.models import User
from .models import Program, Category, FestSettings, PosterTemplate, GlobalPosterTemplate

class PosterTemplateForm(forms.ModelForm):
    class Meta:
        model = PosterTemplate
        fields = ['image_file', 'config']
        widgets = {
            'image_file': forms.FileInput(attrs={'class': 'form-control'}),
            'config': forms.HiddenInput(),
        }

class GlobalPosterTemplateForm(forms.ModelForm):
    class Meta:
        model = GlobalPosterTemplate
        fields = ['image_file', 'config']
        widgets = {
            'image_file': forms.FileInput(attrs={'class': 'form-control'}),
            'config': forms.HiddenInput(),
        }

class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = [
            'name', 'category', 'type', 'stage_type', 'duration', 
            'participant_limit', 'point_weightage_1st', 'point_weightage_2nd',
            'point_weightage_3rd', 'venue', 'schedule', 'max_marks'
        ]
        labels = {
            'name': 'Item Title',
            'category': 'Category',
            'type': 'Type (Single or Group)',
            'stage_type': 'On stage or Offstage',
            'duration': 'Program Duration (Minutes)',
            'participant_limit': 'Maximum Participants from a Team',
            'point_weightage_1st': '1st Rank Weight',
            'point_weightage_2nd': '2nd Rank Weight',
            'point_weightage_3rd': '3rd Rank Weight',
            'venue': 'Venue',
            'schedule': 'Schedule',
            'max_marks': 'Maximum Marks',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Classical Dance'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'stage_type': forms.Select(attrs={'class': 'form-control'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'participant_limit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0 for unlimited'}),
            'point_weightage_1st': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'point_weightage_2nd': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'point_weightage_3rd': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'venue': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Main Stage'}),
            'schedule': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'max_marks': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class JudgeAssignmentForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ['judges']
        widgets = {
            'judges': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['judges'].queryset = User.objects.filter(userprofile__role='judge').order_by('username')
        self.fields['judges'].label = "Assign Judges to this Program"

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'chest_prefix']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Dance'}),
            'chest_prefix': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 100'}),
        }

class FestSettingsForm(forms.ModelForm):
    class Meta:
        model = FestSettings
        fields = ['fest_name', 'year', 'tagline', 'logo', 'point_system', 'dates', 'description']
        widgets = {
            'fest_name': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'point_system': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                   'placeholder': '{"1st": 5, "2nd": 3, "3rd": 1}'}),
        }

class JudgeRegistrationForm(forms.Form):
    first_name  = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}))
    last_name   = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name (optional)'}))
    username    = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Login username'}))
    password    = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter password'}))
    assigned_programs = forms.ModelMultipleChoiceField(
        queryset=Program.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label="Assigned Programs"
    )

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

class UserEditForm(forms.Form):
    first_name  = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name   = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    username    = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password    = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to keep current password'}))
    assigned_programs = forms.ModelMultipleChoiceField(
        queryset=Program.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label="Assigned Programs"
    )
    
    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop('user_instance', None)
        self.is_judge = kwargs.pop('is_judge', True)
        super().__init__(*args, **kwargs)
        if not self.is_judge:
            del self.fields['assigned_programs']
            
        if self.user_instance:
            self.fields['first_name'].initial = self.user_instance.first_name
            self.fields['last_name'].initial = self.user_instance.last_name
            self.fields['username'].initial = self.user_instance.username
            if self.is_judge:
                self.fields['assigned_programs'].initial = self.user_instance.assigned_programs.all()
            
    def clean_username(self):
        uname = self.cleaned_data['username']
        if self.user_instance and self.user_instance.username != uname:
            if User.objects.filter(username=uname).exists():
                raise forms.ValidationError("This username is already taken.")
        return uname

