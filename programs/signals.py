from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from participants.models import Member, Team, CallingList
from programs.models import Program, Stage, FestSettings, ActivityLog
from judging.models import Marksheet
from results.models import Result
from programs.activity_utils import log_activity
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Member)
def member_saved_signal(sender, instance, created, **kwargs):
    if created:
        team_name = instance.team.name if instance.team else 'No Team'
        cat_name = instance.category.name if instance.category else 'General'
        log_activity(
            action_type='member_registered',
            title='Participant Registered',
            description=f"{instance.name} registered under {team_name} ({cat_name}, Chest #{instance.chest_no}).",
            target_model='Member',
            target_id=instance.id,
            metadata={
                'member_id': instance.id,
                'member_name': instance.name,
                'chest_no': instance.chest_no,
                'team_name': team_name,
                'category_name': cat_name
            }
        )

@receiver(post_delete, sender=Member)
def member_deleted_signal(sender, instance, **kwargs):
    team_name = instance.team.name if instance.team else 'No Team'
    cat_name = instance.category.name if instance.category else 'General'
    log_activity(
        action_type='member_deleted',
        title=f"Participant Deleted: {instance.name}",
        description=f"Participant {instance.name} (Chest #{instance.chest_no}, {team_name}) was deleted.",
        target_model='Member',
        target_id=instance.id,
        metadata={
            'member_id': instance.id,
            'member_name': instance.name,
            'chest_no': instance.chest_no,
            'team_name': team_name,
            'category_name': cat_name
        }
    )

@receiver(post_save, sender=Program)
def program_saved_signal(sender, instance, created, **kwargs):
    if created:
        cat_name = instance.category.name if instance.category else 'General'
        log_activity(
            action_type='program_created',
            title=f"Event Created: {instance.name}",
            description=f"New competition event '{instance.name}' ({cat_name}) was created.",
            target_model='Program',
            target_id=instance.id,
            metadata={'program_id': instance.id, 'program_name': instance.name}
        )

@receiver(post_delete, sender=Program)
def program_deleted_signal(sender, instance, **kwargs):
    log_activity(
        action_type='program_deleted',
        title=f"Event Deleted: {instance.name}",
        description=f"Competition event '{instance.name}' was deleted.",
        target_model='Program',
        target_id=instance.id,
        metadata={'program_id': instance.id, 'program_name': instance.name}
    )

@receiver(post_save, sender=Team)
def team_saved_signal(sender, instance, created, **kwargs):
    if created:
        log_activity(
            action_type='team_created',
            title=f"Team Created: {instance.name}",
            description=f"New participating team '{instance.name}' was created.",
            target_model='Team',
            target_id=instance.id,
            metadata={'team_id': instance.id, 'team_name': instance.name}
        )

@receiver(post_delete, sender=Team)
def team_deleted_signal(sender, instance, **kwargs):
    log_activity(
        action_type='team_deleted',
        title=f"Team Deleted: {instance.name}",
        description=f"Participating team '{instance.name}' was deleted.",
        target_model='Team',
        target_id=instance.id,
        metadata={'team_id': instance.id, 'team_name': instance.name}
    )
