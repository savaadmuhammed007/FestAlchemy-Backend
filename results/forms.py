from django import forms
from .models import Result

class ResultForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ['program', 'member', 'total_marks', 'rank', 'published']
        widgets = {
            'program': forms.Select(attrs={'class': 'form-control'}),
            'member': forms.Select(attrs={'class': 'form-control'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control'}),
            'rank': forms.NumberInput(attrs={'class': 'form-control'}),
            'published': forms.CheckboxInput(attrs={'style': 'width:1.2rem;height:1.2rem;'}),
        }
