from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from programs.models import Program
from participants.models import CallingList
from judging.utils import sync_marksheets_for_program, sync_marksheets_for_judge


@receiver(m2m_changed, sender=Program.judges.through)
def on_program_judges_changed(sender, instance, action, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        if isinstance(instance, Program):
            sync_marksheets_for_program(instance)
        elif isinstance(instance, User):
            sync_marksheets_for_judge(instance)


@receiver(post_save, sender=CallingList)
def on_calling_list_saved(sender, instance, **kwargs):
    if instance.status in ('called', 'present') and instance.program_id:
        sync_marksheets_for_program(instance.program)
