from django.db import models
from django.contrib.auth.models import User
import datetime

class FestSettings(models.Model):
    fest_name = models.CharField(max_length=200)
    year = models.IntegerField()
    logo = models.ImageField(upload_to='fest_logos/', null=True, blank=True)
    tagline = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True, help_text='Detailed description shown on the public home page')
    point_system = models.JSONField(default=dict, help_text='ex: {"1st": 5, "2nd": 3, "3rd": 1}')
    dates = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.fest_name} {self.year}"

    class Meta:
        verbose_name_plural = "Fest Settings"

class Category(models.Model):
    name = models.CharField(max_length=100)
    chest_prefix = models.IntegerField(help_text="e.g. 100 for 100 series")
    fest = models.ForeignKey(FestSettings, on_delete=models.CASCADE, null=True, blank=True, related_name='categories')

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"

class Program(models.Model):
    TYPE_CHOICES = [
        ('single', 'Single'),
        ('group', 'Group'),
    ]
    STAGE_CHOICES = [
        ('onstage', 'On stage'),
        ('offstage', 'Offstage'),
    ]

    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='programs')
    fest = models.ForeignKey(FestSettings, on_delete=models.CASCADE, null=True, blank=True, related_name='programs')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='single')
    group_size = models.IntegerField(default=1, blank=True, null=True, help_text="Number of people in group program")
    stage_type = models.CharField(max_length=10, choices=STAGE_CHOICES, default='onstage')
    duration = models.IntegerField(default=5, help_text="Duration in minutes")
    participant_limit = models.IntegerField(default=0, help_text="Maximum participants per team (0 for unlimited)")
    point_weightage_1st = models.IntegerField(default=1, help_text="Point weightage multiplier for 1st rank")
    point_weightage_2nd = models.IntegerField(default=1, help_text="Point weightage multiplier for 2nd rank")
    point_weightage_3rd = models.IntegerField(default=1, help_text="Point weightage multiplier for 3rd rank")
    max_marks = models.IntegerField(default=100)
    schedule = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    judges = models.ManyToManyField(User, related_name='assigned_programs', blank=True, limit_choices_to={'userprofile__role': 'judge'})

    def __str__(self):
        return self.name

    @property
    def calculated_duration_minutes(self):
        if self.stage_type == 'offstage':
            return self.duration
        # onstage
        count = self.registered_members.count()
        return self.duration * count

    @property
    def end_time(self):
        if self.schedule:
            return self.schedule + datetime.timedelta(minutes=self.calculated_duration_minutes)
        return None

def default_poster_config():
    return {
        "program": {"x": 540, "y": 162, "size": 56, "color": "#ffffff"},
        "category": {"x": 540, "y": 243, "size": 35, "color": "#dddddd"},
        "rank1_label": {"x": 540, "y": 405, "size": 30, "color": "#ffd700", "text": "1st"},
        "rank1_name": {"x": 540, "y": 473, "size": 48, "color": "#ffd700"},
        "rank1_team": {"x": 540, "y": 540, "size": 30, "color": "#ffd700"},
        "rank2_label": {"x": 540, "y": 635, "size": 28, "color": "#c0c0c0", "text": "2nd"},
        "rank2_name": {"x": 540, "y": 702, "size": 41, "color": "#c0c0c0"},
        "rank2_team": {"x": 540, "y": 770, "size": 26, "color": "#c0c0c0"},
        "rank3_label": {"x": 540, "y": 864, "size": 28, "color": "#cd7f32", "text": "3rd"},
        "rank3_name": {"x": 540, "y": 932, "size": 41, "color": "#cd7f32"},
        "rank3_team": {"x": 540, "y": 999, "size": 26, "color": "#cd7f32"},
        "result_label": {"x": 540, "y": 1107, "size": 30, "color": "#ffffff", "text": "Result No:"},
        "result_value": {"x": 540, "y": 1175, "size": 30, "color": "#ffffff"},
    }

class PosterTemplate(models.Model):
    program = models.OneToOneField(Program, on_delete=models.CASCADE, related_name='poster_template')
    image_file = models.ImageField(upload_to='poster_templates/')
    config = models.JSONField(default=default_poster_config)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Template for {self.program.name}"

class GlobalPosterTemplate(models.Model):
    image_file = models.ImageField(upload_to='poster_templates/', null=True, blank=True)
    config = models.JSONField(default=default_poster_config)

    def __str__(self):
        return "Global Poster Template"

class ProgramGradeSetting(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='grade_settings')
    grade_name = models.CharField(max_length=50)
    min_marks = models.FloatField()
    points = models.IntegerField(default=0)

    class Meta:
        ordering = ['-min_marks']
        unique_together = ('program', 'grade_name')

    def __str__(self):
        return f"{self.program.name} - {self.grade_name} (>= {self.min_marks} marks, {self.points} pts)"

class Stage(models.Model):
    STAGE_TYPE_CHOICES = [
        ('onstage', 'On stage'),
        ('offstage', 'Offstage'),
    ]
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=10, choices=STAGE_TYPE_CHOICES, default='onstage')
    fest = models.ForeignKey(FestSettings, on_delete=models.CASCADE, null=True, blank=True, related_name='stages')

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'fest')
