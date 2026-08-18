from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def log_activity(action_type, title, description="", user=None, target_model="", target_id=None, metadata=None, fest=None):
    """
    Safely log an activity event to the ActivityLog model without throwing uncaught exceptions.
    """
    from programs.models import ActivityLog, FestSettings
    try:
        user_name = ""
        user_obj = None

        if user:
            if getattr(user, 'is_authenticated', False):
                user_obj = user
                first_last = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
                user_name = first_last if first_last else getattr(user, 'username', 'User')
            elif isinstance(user, str):
                user_name = user

        if not user_name:
            user_name = "Admin"

        if not fest:
            fest = FestSettings.objects.first()

        # Deduplication check (within 2 seconds)
        if target_model and target_id:
            from datetime import timedelta
            recent_duplicate = ActivityLog.objects.filter(
                action_type=action_type,
                target_model=target_model,
                target_id=target_id,
                created_at__gte=timezone.now() - timedelta(seconds=2)
            ).first()
            if recent_duplicate:
                return recent_duplicate

        activity = ActivityLog.objects.create(
            fest=fest,
            user=user_obj,
            user_name=user_name,
            action_type=action_type,
            title=title,
            description=description,
            target_model=target_model,
            target_id=target_id,
            metadata=metadata or {},
        )
        return activity
    except Exception as e:
        logger.warning(f"Failed to log activity '{action_type}': {e}")
        return None


def backfill_activity_logs():
    """
    Backfill realistic initial activity log items from existing database records
    if the ActivityLog table is currently empty.
    """
    from programs.models import ActivityLog, Program, FestSettings, Stage
    from results.models import Result
    from judging.models import Marksheet
    from participants.models import Member, CallingList, Team

    if ActivityLog.objects.exists():
        return

    fest = FestSettings.objects.first()

    # 1. Backfill published results
    published_results = Result.objects.filter(published=True).select_related('program', 'member', 'member__team', 'program__category')
    programs_seen = set()
    for res in published_results:
        prog = res.program
        if prog.id in programs_seen:
            continue
        programs_seen.add(prog.id)
        
        # Get rank 1 winner if available
        rank1 = Result.objects.filter(program=prog, rank=1).select_related('member', 'member__team').first()
        winner_info = f"1st: {rank1.member.name} ({rank1.member.team.name})" if rank1 else "Results published"
        
        log_activity(
            action_type='result_published',
            title=f"Results Published: {prog.name}",
            description=f"Results finalized and published for {prog.name} ({prog.category.name}). {winner_info}.",
            target_model='Program',
            target_id=prog.id,
            metadata={
                'program_id': prog.id,
                'program_name': prog.name,
                'category_name': prog.category.name,
                'winner_name': rank1.member.name if rank1 else '',
                'winner_team': rank1.member.team.name if rank1 else '',
                'rank1_chest': rank1.member.chest_no if rank1 else None,
            },
            fest=fest
        )

    # 2. Backfill submitted marksheets
    submitted_sheets = Marksheet.objects.filter(submitted=True).select_related('program', 'judge', 'member', 'member__team')[:15]
    for sheet in submitted_sheets:
        score_val = sheet.marks.get('total') if isinstance(sheet.marks, dict) else sheet.marks
        log_activity(
            action_type='marks_submitted',
            title=f"Evaluation Submitted",
            description=f"Judge {sheet.judge.username} submitted marks ({score_val} pts) for Chest #{sheet.member.chest_no} ({sheet.member.name}) in {sheet.program.name}.",
            user=sheet.judge,
            target_model='Marksheet',
            target_id=sheet.id,
            metadata={
                'program_id': sheet.program.id,
                'program_name': sheet.program.name,
                'chest_no': sheet.member.chest_no,
                'member_name': sheet.member.name,
                'judge_username': sheet.judge.username,
                'score': score_val
            },
            fest=fest
        )

    # 3. Backfill lot calling
    called_lots = CallingList.objects.filter(status='called').select_related('program', 'member', 'member__team')[:10]
    for calling in called_lots:
        code = calling.calling_code.split('-')[1] if ('-' in (calling.calling_code or '')) else (calling.calling_code or 'Lot')
        log_activity(
            action_type='lot_called',
            title=f"Lot Assigned: {calling.program.name}",
            description=f"Lot code {code} drawn for {calling.member.name} (Chest #{calling.member.chest_no}, {calling.member.team.name}).",
            target_model='CallingList',
            target_id=calling.id,
            metadata={
                'program_id': calling.program.id,
                'program_name': calling.program.name,
                'chest_no': calling.member.chest_no,
                'calling_code': code,
                'team_name': calling.member.team.name
            },
            fest=fest
        )

    # 4. Backfill registered members
    recent_members = Member.objects.select_related('team', 'category')[:10]
    for mem in recent_members:
        log_activity(
            action_type='member_registered',
            title=f"Participant Registered",
            description=f"{mem.name} registered under {mem.team.name} ({mem.category.name}, Chest #{mem.chest_no}).",
            target_model='Member',
            target_id=mem.id,
            metadata={
                'member_id': mem.id,
                'member_name': mem.name,
                'chest_no': mem.chest_no,
                'team_name': mem.team.name,
                'category_name': mem.category.name
            },
            fest=fest
        )

    # 5. Backfill scheduled programs
    scheduled_progs = Program.objects.filter(schedule__isnull=False).select_related('category')[:8]
    for sp in scheduled_progs:
        date_str = sp.schedule.strftime("%b %d, %I:%M %p") if sp.schedule else ""
        log_activity(
            action_type='program_scheduled',
            title=f"Program Scheduled: {sp.name}",
            description=f"{sp.name} ({sp.category.name}) scheduled at {sp.venue or 'Main Stage'} for {date_str}.",
            target_model='Program',
            target_id=sp.id,
            metadata={
                'program_id': sp.id,
                'program_name': sp.name,
                'venue': sp.venue or 'Main Stage',
                'schedule': str(sp.schedule)
            },
            fest=fest
        )

    # 6. Backfill fest settings setup
    if fest:
        log_activity(
            action_type='settings_updated',
            title=f"Fest Initialized: {fest.fest_name}",
            description=f"Fest settings configured for {fest.fest_name} {fest.year}.",
            target_model='FestSettings',
            target_id=fest.id,
            metadata={'fest_name': fest.fest_name, 'year': fest.year},
            fest=fest
        )
