from django.db import models
from django.contrib.auth.models import User
from programs.models import Program
from participants.models import Member

class Marksheet(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='marksheets')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='marksheets')
    judge = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_marksheets')
    marks = models.JSONField(default=dict, help_text="Store criteria name and mark mapping or just total")
    submitted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.program.name} - {self.member.chest_no} (Judge: {self.judge.username})"
