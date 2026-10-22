def sync_marksheets_for_program(program):
    """
    Ensures that for every assigned judge in program.judges and every participant
    in CallingList with status in ('called', 'present'), a Marksheet exists.
    Also cleans up unsubmitted draft marksheets of judges who were unassigned from this program.
    Returns the count of newly created marksheets.
    """
    if not program:
        return 0
        
    from judging.models import Marksheet
    from participants.models import CallingList

    judges = list(program.judges.all())
    if not judges:
        # If no judges assigned, clear any lingering unsubmitted drafts if any exist
        if Marksheet.objects.filter(program=program, submitted=False).exists():
            Marksheet.objects.filter(program=program, submitted=False).delete()
        return 0

    called_callings = list(
        CallingList.objects.filter(program=program, status__in=['called', 'present']).select_related('member')
    )
    
    # Clean up unsubmitted marksheets of judges who are no longer assigned to this program
    Marksheet.objects.filter(program=program, submitted=False).exclude(judge__in=judges).delete()

    if not called_callings:
        return 0

    # Find existing marksheets for this program
    existing_sheets = set(
        Marksheet.objects.filter(program=program)
        .values_list('judge_id', 'member_id')
    )

    # Create missing marksheets for each assigned judge and called participant
    new_marksheets = []
    for judge in judges:
        for calling in called_callings:
            if (judge.id, calling.member_id) not in existing_sheets:
                new_marksheets.append(
                    Marksheet(
                        program=program,
                        judge=judge,
                        member=calling.member
                    )
                )
                existing_sheets.add((judge.id, calling.member_id))

    if new_marksheets:
        created = Marksheet.objects.bulk_create(new_marksheets, ignore_conflicts=True)
        return len(created)
    return 0


def sync_marksheets_for_judge(judge_user):
    """
    Ensures marksheets exist for all programs assigned to this judge
    where participants have been called.
    """
    if not judge_user:
        return
    from programs.models import Program
    assigned_programs = Program.objects.filter(judges=judge_user)
    for program in assigned_programs:
        sync_marksheets_for_program(program)
