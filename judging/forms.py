from django import forms
from .models import Marksheet

class MarksheetForm(forms.ModelForm):
    score = forms.FloatField(
        label="Score",
        min_value=0.0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Enter marks (e.g. 85.5)'})
    )

    class Meta:
        model = Marksheet
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set max_value dynamically based on the program's max_marks
        if self.instance and self.instance.program:
            max_marks = self.instance.program.max_marks
            self.fields['score'].max_value = max_marks
            self.fields['score'].help_text = f"Maximum allowed marks: {max_marks}"
            
            # Load initial value from marks JSON field
            raw = self.instance.marks
            if isinstance(raw, dict):
                total = raw.get('total')
                if total is None:
                    try:
                        total = sum(float(v) for v in raw.values() if str(v).replace('.', '', 1).isdigit())
                    except Exception:
                        total = 0.0
                self.fields['score'].initial = total
            else:
                try:
                    self.fields['score'].initial = float(raw) if raw else 0.0
                except (TypeError, ValueError):
                    self.fields['score'].initial = 0.0

    def clean_score(self):
        score = self.cleaned_data.get('score')
        if self.instance and self.instance.program:
            max_marks = self.instance.program.max_marks
            if score > max_marks:
                raise forms.ValidationError(f"Marks cannot exceed maximum allowed marks ({max_marks})")
        return score

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.marks = {'total': self.cleaned_data['score']}
        if commit:
            instance.save()
        return instance
