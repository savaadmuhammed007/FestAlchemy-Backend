from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teamlead', 'Team Lead'),
        ('judge', 'Judge'),
        ('user', 'Public User'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    team = models.ForeignKey('participants.Team', on_delete=models.SET_NULL, null=True, blank=True)
    fest = models.ForeignKey('programs.FestSettings', on_delete=models.CASCADE, null=True, blank=True, related_name='user_profiles')

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
