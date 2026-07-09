from django.db import models
from programs.models import Program
from participants.models import Member, Team

class Result(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='results')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='results')
    total_marks = models.FloatField()
    rank = models.IntegerField(blank=True, null=True)
    points = models.FloatField(default=0)
    judge_code = models.CharField(max_length=10, blank=True)
    published = models.BooleanField(default=False)
    grade = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.program.name} - Rank {self.rank}: {self.member.name}"

class TeamPoints(models.Model):
    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name='points')
    total_points = models.IntegerField(default=0)
    breakdown = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.team.name} - {self.total_points} pts"


from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Result)
def result_saved(sender, instance, **kwargs):
    from .utils import recalculate_team_points
    recalculate_team_points()

@receiver(post_delete, sender=Result)
def result_deleted(sender, instance, **kwargs):
    from .utils import recalculate_team_points
    recalculate_team_points()

