from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from accounts.decorators import role_required
from django.contrib.auth.models import User
from .models import Program, Category, FestSettings, PosterTemplate, GlobalPosterTemplate, ProgramGradeSetting
from .forms import ProgramForm, CategoryForm, FestSettingsForm, PosterTemplateForm, GlobalPosterTemplateForm, JudgeRegistrationForm, UserEditForm
from participants.models import CallingList, Member, Team
from participants.forms import TeamForm, MemberForm
from judging.models import Marksheet
from results.models import Result, TeamPoints
from results.forms import ResultForm
from results.utils import generate_winner_poster
from django.db.models import Exists, OuterRef, Sum, Count


# ─────────────────────────────────────────────
#  ADMIN DASHBOARD (overview cards)
# ─────────────────────────────────────────────
@role_required('admin')
def admin_dashboard(request):
    from django.db.models import Sum, Count
    team_points = TeamPoints.objects.select_related('team').order_by('-total_points')
    member_points = (
        Result.objects.filter(published=True)
        .values('member__id', 'member__name', 'member__team__name')
        .annotate(total=Sum('points'), events=Count('id'))
        .order_by('-total')[:20]
    )
    return render(request, 'programs/admin_dashboard.html', {
        'programs_count': Program.objects.count(),
        'categories_count': Category.objects.count(),
        'teams_count': Team.objects.count(),
        'members_count': Member.objects.count(),
        'marksheets_pending': Marksheet.objects.filter(submitted=False).count(),
        'results_count': Result.objects.count(),
        'programs': Program.objects.select_related('category').all(),
        'team_points': team_points,
        'member_points': member_points,
    })


# ─────────────────────────────────────────────
#  FEST SETTINGS
# ─────────────────────────────────────────────
@role_required('admin')
def fest_settings(request):
    obj = FestSettings.objects.first()
    form = FestSettingsForm(request.POST or None, request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, "Fest settings saved.")
        return redirect('fest_settings')
    
    # User lists
    judges = User.objects.filter(userprofile__role='judge').prefetch_related('assigned_programs').order_by('username')
    teamleads = User.objects.filter(userprofile__role='teamlead').select_related('userprofile__team').order_by('username')
    
    active_tab = request.GET.get('tab', 'event')
    
    return render(request, 'programs/fest_settings.html', {
        'form': form,
        'obj': obj,
        'judges': judges,
        'teamleads': teamleads,
        'active_tab': active_tab,
    })


# ─────────────────────────────────────────────
#  CATEGORY CRUD
# ─────────────────────────────────────────────
@role_required('admin')
def category_list(request):
    categories = Category.objects.annotate_or_plain = Category.objects.all()
    return render(request, 'programs/category_list.html', {'categories': categories})

@role_required('admin')
def category_add(request):
    form = CategoryForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Category added.")
        return redirect('category_list')
    return render(request, 'programs/category_form.html', {'form': form, 'action': 'Add'})

@role_required('admin')
def category_edit(request, pk):
    obj = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, "Category updated.")
        return redirect('category_list')
    return render(request, 'programs/category_form.html', {'form': form, 'action': 'Edit'})

@role_required('admin')
def category_delete(request, pk):
    obj = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, "Category deleted.")
        return redirect('category_list')
    return render(request, 'programs/confirm_delete.html', {'obj': obj, 'type': 'Category'})


# ─────────────────────────────────────────────
#  PROGRAM CRUD
# ─────────────────────────────────────────────
@role_required('admin')
def program_list(request):
    qs = Program.objects.select_related('category').all()
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '').strip()
    if q:
        qs = qs.filter(name__icontains=q)
    if cat:
        qs = qs.filter(category__id=cat)
    categories = Category.objects.all()
    return render(request, 'programs/program_list.html', {
        'programs': qs, 'categories': categories, 'q': q, 'selected_cat': cat
    })

@role_required('admin')
def schedule_list(request):
    qs = Program.objects.select_related('category').order_by('schedule')
    cat = request.GET.get('category', '').strip()
    has_venue = request.GET.get('has_venue', '').strip()
    if cat:
        qs = qs.filter(category__id=cat)
    if has_venue == 'yes':
        qs = qs.exclude(venue='')
    elif has_venue == 'no':
        qs = qs.filter(venue='')
    categories = Category.objects.all()
    return render(request, 'programs/schedule_list.html', {
        'programs': qs, 'categories': categories,
        'sel_cat': cat, 'sel_venue': has_venue,
    })

@role_required('admin')
def schedule_update(request, pk):
    """AJAX endpoint: update schedule + venue for a single program."""
    from django.http import JsonResponse
    program = get_object_or_404(Program, pk=pk)
    if request.method == 'POST':
        schedule_val = request.POST.get('schedule', '').strip()
        venue_val = request.POST.get('venue', '').strip()
        from django.utils.dateparse import parse_datetime
        if schedule_val:
            dt = parse_datetime(schedule_val)
            program.schedule = dt
        else:
            program.schedule = None
        program.venue = venue_val
        program.save()
        return JsonResponse({
            'status': 'ok',
            'schedule': program.schedule.strftime('%d %b %Y, %H:%M') if program.schedule else '',
            'venue': program.venue,
        })
    return JsonResponse({'status': 'error'}, status=400)

@role_required('admin')
def program_add(request):
    form = ProgramForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Program added.")
        return redirect('program_list')
    return render(request, 'programs/program_form.html', {'form': form, 'action': 'Add'})

@role_required('admin')
def program_edit(request, pk):
    obj = get_object_or_404(Program, pk=pk)
    form = ProgramForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, "Program updated.")
        return redirect('program_list')
    return render(request, 'programs/program_form.html', {'form': form, 'action': 'Edit', 'obj': obj})

@role_required('admin')
def program_delete(request, pk):
    obj = get_object_or_404(Program, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, "Program deleted.")
        return redirect('program_list')
    return render(request, 'programs/confirm_delete.html', {'obj': obj, 'type': 'Program'})


# ─────────────────────────────────────────────
#  TEAM CRUD (admin manages teams)
# ─────────────────────────────────────────────
@role_required('admin')
def team_list(request):
    teams = Team.objects.prefetch_related('members').all()
    return render(request, 'programs/team_list.html', {'teams': teams})

@role_required('admin')
def team_add(request):
    from django.db import transaction
    from participants.forms import TeamLeadRegistrationForm
    from accounts.models import UserProfile

    user_form = TeamLeadRegistrationForm(request.POST or None)
    team_name_error = None

    if request.method == 'POST':
        team_name = request.POST.get('team_name', '').strip()
        if not team_name:
            team_name_error = "Team name is required."

        if user_form.is_valid() and not team_name_error:
            try:
                with transaction.atomic():
                    # 1. Create the User
                    new_user = user_form.save_user()
                    # 2. Create (or update) their UserProfile with teamlead role
                    UserProfile.objects.update_or_create(
                        user=new_user,
                        defaults={'role': 'teamlead'}
                    )
                    # 3. Create the Team linked to the new user
                    Team.objects.create(name=team_name, teamlead=new_user)
                messages.success(request, f"Team '{team_name}' created. Team Lead account '{new_user.username}' registered.")
                return redirect('team_list')
            except Exception as e:
                messages.error(request, f"Error: {e}")

    return render(request, 'programs/team_add.html', {
        'user_form': user_form,
        'team_name_error': team_name_error,
        'team_name_value': request.POST.get('team_name', ''),
    })

@role_required('admin')
def team_edit(request, pk):
    obj = get_object_or_404(Team, pk=pk)
    form = TeamForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, "Team updated.")
        return redirect('team_list')
    return render(request, 'programs/team_form.html', {'form': form, 'action': 'Edit', 'obj': obj})

@role_required('admin')
def team_delete(request, pk):
    obj = get_object_or_404(Team, pk=pk)
    if request.method == 'POST':
        from django.db.models.signals import post_save, post_delete
        from results.models import Result, result_saved, result_deleted
        from results.utils import recalculate_team_points
        
        # Disconnect signals to prevent recalculating points mid-cascade
        post_save.disconnect(result_saved, sender=Result)
        post_delete.disconnect(result_deleted, sender=Result)
        
        try:
            from results.models import TeamPoints
            TeamPoints.objects.filter(team=obj).delete()
            obj.delete()
        finally:
            # Reconnect signals
            post_save.connect(result_saved, sender=Result)
            post_delete.connect(result_deleted, sender=Result)
            
        # Recalculate once after the team is completely deleted
        recalculate_team_points()
        
        messages.success(request, "Team deleted.")
        return redirect('team_list')
    return render(request, 'programs/confirm_delete.html', {'obj': obj, 'type': 'Team'})


# ─────────────────────────────────────────────
#  MEMBER MANAGEMENT (admin view all members)
# ─────────────────────────────────────────────
@role_required('admin')
def member_list(request):
    qs = Member.objects.select_related('team', 'category').all()
    q = request.GET.get('q', '').strip()
    team = request.GET.get('team', '').strip()
    category = request.GET.get('category', '').strip()
    if q:
        qs = qs.filter(name__icontains=q)
    if team:
        qs = qs.filter(team__id=team)
    if category:
        qs = qs.filter(category__id=category)
    teams = Team.objects.all()
    categories = Category.objects.all()
    return render(request, 'programs/member_list.html', {
        'members': qs, 'teams': teams, 'categories': categories,
        'q': q, 'sel_team': team, 'sel_cat': category
    })

@role_required('admin')
def member_delete(request, pk):
    obj = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, "Member removed.")
        return redirect('member_list')
    return render(request, 'programs/confirm_delete.html', {'obj': obj, 'type': 'Member'})


# ─────────────────────────────────────────────
#  MARKSHEET MANAGEMENT
# ─────────────────────────────────────────────
@role_required('admin')
def marksheet_list(request):
    """List all programs to see their marksheets."""
    programs = Program.objects.all().order_by('category', 'name')
    return render(request, 'programs/marksheet_list.html', {'programs': programs})

@role_required('admin')
def marksheet_program_detail(request, program_id):
    """Detailed view of marksheets for a specific program."""
    program = get_object_or_404(Program, id=program_id)
    sheets = Marksheet.objects.filter(program=program).select_related('member', 'judge')
    
    # Enrich with judge_code (from CallingList)
    from participants.models import CallingList
    for s in sheets:
        calling = CallingList.objects.filter(program=program, member=s.member).first()
        if calling and '-' in calling.calling_code:
            s.judge_code = calling.calling_code.split('-')[1]
        else:
            s.judge_code = calling.calling_code if calling else "N/A"

    return render(request, 'programs/marksheet_program_detail.html', {
        'program': program,
        'sheets': sheets
    })


# ─────────────────────────────────────────────
#  RESULTS CRUD + COMPUTE
# ─────────────────────────────────────────────
@role_required('admin')
def result_list(request):
    from django.db.models import Q
    qs = Program.objects.filter(
        Q(results__isnull=False) | Q(marksheets__isnull=False)
    ).distinct().select_related('category')
    
    cat = request.GET.get('category', '').strip()
    published = request.GET.get('published', '').strip()
    if cat:
        qs = qs.filter(category__id=cat)
        
    declared_programs = []
    pending_programs = []
    for program in qs:
        has_results = program.results.exists()
        is_published = Result.objects.filter(program=program, published=True).exists()
        
        total_sheets = Marksheet.objects.filter(program=program).count()
        submitted_sheets = Marksheet.objects.filter(program=program, submitted=True).count()
        
        if published == 'yes' and not is_published:
            continue
        if published == 'no' and (is_published or not has_results):
            continue
            
        program.has_results = has_results
        program.is_published = is_published
        program.total_sheets = total_sheets
        program.submitted_sheets = submitted_sheets
        
        if has_results:
            declared_programs.append(program)
        else:
            pending_programs.append(program)
        
    categories = Category.objects.all()
    return render(request, 'programs/result_list.html', {
        'declared_programs': declared_programs,
        'pending_programs': pending_programs,
        'categories': categories,
        'sel_cat': cat, 
        'sel_published': published,
    })

@role_required('admin')
def result_program_detail(request, program_id):
    program = get_object_or_404(Program, id=program_id)
    qs = Result.objects.filter(program=program).select_related('member', 'member__team').order_by('rank')
    published = request.GET.get('published', '').strip()
    team = request.GET.get('team', '').strip()
    if published == 'yes':
        qs = qs.filter(published=True)
    elif published == 'no':
        qs = qs.filter(published=False)
    if team:
        qs = qs.filter(member__team__id=team)
    
    results_list = list(qs)
    for r in results_list:
        sheets = Marksheet.objects.filter(program=program, member=r.member).select_related('judge')
        r.judges_scores = []
        for s in sheets:
            raw = s.marks
            if isinstance(raw, dict):
                try:
                    total = sum(float(v) for v in raw.values() if str(v).replace('.', '', 1).isdigit())
                except Exception:
                    total = 0
            else:
                try:
                    total = float(raw)
                except (TypeError, ValueError):
                    total = 0
            r.judges_scores.append({
                'judge': s.judge.first_name or s.judge.username,
                'marks': total,
                'submitted': s.submitted
            })

    teams = Team.objects.filter(members__results__program=program).distinct()
    return render(request, 'programs/result_program_detail.html', {
        'program': program, 'results': results_list,
        'teams': teams, 'sel_published': published, 'sel_team': team,
    })

@role_required('admin')
def result_add(request):
    form = ResultForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Result record added.")
        return redirect('result_list')
    return render(request, 'programs/result_form.html', {'form': form, 'action': 'Add'})

@role_required('admin')
def result_edit(request, pk):
    obj = get_object_or_404(Result, pk=pk)
    form = ResultForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, "Result updated.")
        return redirect('result_list')
    return render(request, 'programs/result_form.html', {'form': form, 'action': 'Edit', 'obj': obj})

@role_required('admin')
def result_delete(request, pk):
    obj = get_object_or_404(Result, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, "Result deleted.")
        return redirect('result_list')
    return render(request, 'programs/confirm_delete.html', {'obj': obj, 'type': 'Result'})

@role_required('admin')
def compute_results(request, program_id):
    """Auto-compute ranks from submitted marksheets and update TeamPoints."""
    program = get_object_or_404(Program, pk=program_id)
    sheets = Marksheet.objects.filter(program=program, submitted=True)

    if not sheets.exists():
        messages.error(request, "No submitted marksheets found for this program.")
        return redirect('result_list')

    # Aggregate marks per member
    from collections import defaultdict
    totals = defaultdict(float)
    counts = defaultdict(int)
    for sheet in sheets:
        raw = sheet.marks
        if isinstance(raw, dict):
            total = sum(float(v) for v in raw.values() if str(v).replace('.', '', 1).isdigit())
        else:
            try:
                total = float(raw)
            except (TypeError, ValueError):
                total = 0
        totals[sheet.member_id] += total
        counts[sheet.member_id] += 1

    # Average marks across judges then rank
    averaged = {mid: totals[mid] / counts[mid] for mid in totals}
    ranked = sorted(averaged.items(), key=lambda x: x[1], reverse=True)

    # Get point system from FestSettings
    fest = FestSettings.objects.first()
    point_map = fest.point_system if fest else {}

    # Get program-specific grading rules
    grade_rules = list(program.grade_settings.all())

    # Pre-compute entries, grades, and base points
    computed_entries = []
    for rank_idx, (member_id, avg_marks) in enumerate(ranked, start=1):
        scaled = (avg_marks / program.max_marks) * 100 if program.max_marks > 0 else avg_marks
        
        # Grade calculation
        if scaled >= 95:
            grade_name = "A+"
        elif scaled >= 85:
            grade_name = "A"
        elif scaled >= 75:
            grade_name = "B"
        elif scaled >= 65:
            grade_name = "C"
        elif scaled >= 50:
            grade_name = "D"
        else:
            grade_name = None

        # Base points calculation
        if program.type == 'group':
            if grade_name == "A+":
                pts = 20
            elif grade_name == "A":
                pts = 15
            elif grade_name == "B":
                pts = 10
            elif grade_name == "C":
                pts = 5
            elif grade_name == "D":
                pts = 3
            else:
                pts = 0
        else:  # individual / single
            if grade_name == "A+":
                pts = 10
            elif grade_name == "A":
                pts = 8
            elif grade_name == "B":
                pts = 6
            elif grade_name == "C":
                pts = 4
            elif grade_name == "D":
                pts = 2
            else:
                pts = 0

        computed_entries.append({
            'member_id': member_id,
            'avg_marks': avg_marks,
            'rank': rank_idx,
            'grade_name': grade_name,
            'base_pts': pts
        })

    # Count frequencies of each grade
    grade_counts = {}
    for entry in computed_entries:
        g = entry['grade_name']
        if g:
            grade_counts[g] = grade_counts.get(g, 0) + 1

    with transaction.atomic():
        Result.objects.filter(program=program).delete()
        for entry in computed_entries:
            member_id = entry['member_id']
            avg_marks = entry['avg_marks']
            rank_idx = entry['rank']
            grade_name = entry['grade_name']
            pts = entry['base_pts']

            # Position bonus points (only if they have a grade and that grade is shared with others)
            if grade_name and grade_counts.get(grade_name, 0) > 1:
                if rank_idx == 1:
                    pts += 3
                elif rank_idx == 2:
                    pts += 1

            # Get judge_code from CallingList
            calling = CallingList.objects.filter(program=program, member_id=member_id).first()
            jcod = ""
            if calling:
                jcod = calling.calling_code.split('-')[1] if '-' in calling.calling_code else calling.calling_code

            Result.objects.create(
                program=program,
                member_id=member_id,
                total_marks=round(avg_marks, 2),
                rank=rank_idx,
                points=pts,
                grade=grade_name,
                judge_code=jcod,
                published=False,
            )

    from results.utils import recalculate_team_points
    recalculate_team_points()

    messages.success(request, f"Results computed for '{program.name}'. {len(ranked)} entries ranked.")
    return redirect('result_list')

@role_required('admin')
def toggle_publish_program(request, program_id):
    program = get_object_or_404(Program, id=program_id)
    results = program.results.all()
    if not results.exists():
        messages.warning(request, "No results found for this program.")
        return redirect('result_list')
    
    if results.filter(published=True).exists():
        results.update(published=False)
        messages.success(request, f"Results for '{program.name}' hidden.")
    else:
        results.update(published=True)
        messages.success(request, f"Results for '{program.name}' published.")
    
    from results.utils import recalculate_team_points
    recalculate_team_points()
    
    return redirect('result_list')


# ─────────────────────────────────────────────
#  SCRATCH-CARD CALLING UI
# ─────────────────────────────────────────────
@role_required('admin')
def call_participant(request, program_id):
    program = get_object_or_404(Program, id=program_id)
    if program.results.exists():
        messages.error(request, "Cannot spin lot for a program with finalized results.")
        return redirect('spin_lot_list')

    # Pregenerate calling codes for all registered members
    CallingList.pregenerate_for_program(program)

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        member = get_object_or_404(Member, id=member_id)
        calling, _ = CallingList.objects.get_or_create(program=program, member=member)
        calling.status = 'called'
        calling.save()
        for judge in program.judges.all():
            Marksheet.objects.get_or_create(program=program, judge=judge, member=member)
            
        import json
        from django.http import JsonResponse
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('accept') == 'application/json':
            return JsonResponse({'status': 'ok', 'code': calling.calling_code.split('-')[1] if '-' in calling.calling_code else calling.calling_code})
            
        messages.success(request, f"{member.name} ({member.chest_no}) called for {program.name}")
        return redirect('call_participant', program_id=program.id)

    callings = CallingList.objects.filter(program=program).select_related('member')
    status_map = {c.member_id: c.status for c in callings}
    code_map = {c.member_id: c.calling_code.split('-')[1] if '-' in c.calling_code else c.calling_code for c in callings}
    
    # Annotate members
    members = list(program.registered_members.all())
    for member in members:
        member.called = status_map.get(member.id) == 'called'
        member.judge_code = code_map.get(member.id, "??")
    
    return render(request, 'programs/spin_lot.html', {
        'program': program,
        'members': members,
    })

@role_required('admin')
def spin_lot_list(request):
    programs = Program.objects.select_related('category').prefetch_related('registered_members', 'calling_lists').all()
    return render(request, 'programs/spin_lot_list.html', {
        'programs': programs,
    })

@role_required('admin')
def grade_settings_list(request):
    programs = Program.objects.select_related('category').prefetch_related('grade_settings').all()
    return render(request, 'programs/grade_settings_list.html', {
        'programs': programs,
    })

@role_required('admin')
def grade_setting_edit(request, program_id):
    program = get_object_or_404(Program, id=program_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            grade_name = request.POST.get('grade_name', '').strip()
            try:
                min_marks = float(request.POST.get('min_marks', 0))
                points = int(request.POST.get('points', 0))
            except ValueError:
                messages.error(request, "Invalid marks or points value.")
                return redirect('grade_setting_edit', program_id=program.id)

            if min_marks < 0 or min_marks > program.max_marks:
                messages.error(request, f"Minimum marks must be between 0 and {program.max_marks}.")
                return redirect('grade_setting_edit', program_id=program.id)

            # Prevent duplicate grade names for the same program
            if ProgramGradeSetting.objects.filter(program=program, grade_name=grade_name).exists():
                messages.error(request, f"A grading rule for '{grade_name}' already exists.")
            else:
                ProgramGradeSetting.objects.create(
                    program=program,
                    grade_name=grade_name,
                    min_marks=min_marks,
                    points=points
                )
                messages.success(request, f"Grading rule for '{grade_name}' added successfully.")
        elif action == 'delete':
            rule_id = request.POST.get('rule_id')
            rule = get_object_or_404(ProgramGradeSetting, id=rule_id, program=program)
            rule.delete()
            messages.success(request, "Grading rule deleted.")
            
        return redirect('grade_setting_edit', program_id=program.id)

    rules = program.grade_settings.all()
    return render(request, 'programs/grade_setting_edit.html', {
        'program': program,
        'rules': rules,
    })

@role_required('admin')
def respin_program(request, program_id):
    program = get_object_or_404(Program, id=program_id)

    with transaction.atomic():
        # Clear calling list, marksheets, and results for all members in this program
        CallingList.objects.filter(program=program).delete()
        Marksheet.objects.filter(program=program).delete()
        Result.objects.filter(program=program).delete()
        
        # Recalculate team points
        from results.utils import recalculate_team_points
        recalculate_team_points()

    messages.success(request, f"Lot codes reset for all participants in '{program.name}'. You can now spin again.")
    return redirect('call_participant', program_id=program.id)

@role_required('admin')
def generate_poster(request, program_id):
    import io
    program = get_object_or_404(Program, id=program_id)
    results = Result.objects.filter(program=program).order_by('rank')[:3]
    fest = FestSettings.objects.first()
    fest_name = fest.fest_name if fest else "FestAlchemy"
    
    # Try to get template (Program-specific first, then Global)
    template = PosterTemplate.objects.filter(program=program).first()
    if not template:
        template = GlobalPosterTemplate.objects.first()
    
    template_path = template.image_file.path if template and template.image_file else None
    config = template.config if template else None
    
    img = generate_winner_poster(template_path, program, results, fest_name, config=config)
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    
    response = HttpResponse(buf.getvalue(), content_type='image/png')
    if request.GET.get('download'):
        response['Content-Disposition'] = f'attachment; filename="{program.name}_winners.png"'
    return response

@role_required('admin')
def global_poster_settings(request):
    template = GlobalPosterTemplate.objects.first()
    # Create if not exists
    if not template:
        template = GlobalPosterTemplate.objects.create()
    
    if request.method == 'POST':
        form = GlobalPosterTemplateForm(request.POST, request.FILES, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, "Global poster settings saved.")
            return redirect('global_poster_settings')
    else:
        form = GlobalPosterTemplateForm(instance=template)
    
    return render(request, 'programs/poster_settings.html', {
        'program': {'name': 'GLOBAL TEMPLATE'}, # Dummy for designer
        'template': template,
        'form': form,
        'config_json': template.config,
        'is_global': True
    })

@role_required('admin')
def poster_settings(request, program_id):
    program = get_object_or_404(Program, id=program_id)
    template = PosterTemplate.objects.filter(program=program).first()
    
    if request.method == 'POST':
        form = PosterTemplateForm(request.POST, request.FILES, instance=template)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.program = program
            obj.save()
            messages.success(request, "Poster settings saved.")
            return redirect('poster_settings', program_id=program.id)
    else:
        form = PosterTemplateForm(instance=template)
    
    return render(request, 'programs/poster_settings.html', {
        'program': program,
        'template': template,
        'form': form,
        'config_json': template.config if template else None
    })

# ─────────────────────────────────────────────
#  USER MANAGEMENT (admin manages judges and team leads)
# ─────────────────────────────────────────────
@role_required('admin')
def judge_add(request):
    if request.method == 'POST':
        form = JudgeRegistrationForm(request.POST)
        if form.is_valid():
            from django.db import transaction
            from accounts.models import UserProfile
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name']
                    )
                    UserProfile.objects.create(user=user, role='judge')
                    # Update assigned programs
                    programs = form.cleaned_data['assigned_programs']
                    for prog in programs:
                        prog.judges.add(user)
                messages.success(request, f"Judge '{user.username}' registered successfully.")
                return redirect('/admin-panel/settings/?tab=users')
            except Exception as e:
                messages.error(request, f"Error: {e}")
    else:
        form = JudgeRegistrationForm()
    return render(request, 'programs/generic_form.html', {'form': form, 'action': 'Add', 'type': 'Judge'})

@role_required('admin')
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    is_judge = hasattr(user, 'userprofile') and user.userprofile.role == 'judge'
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, user_instance=user, is_judge=is_judge)
        if form.is_valid():
            from django.db import transaction
            try:
                with transaction.atomic():
                    user.username = form.cleaned_data['username']
                    user.first_name = form.cleaned_data['first_name']
                    user.last_name = form.cleaned_data['last_name']
                    pw = form.cleaned_data.get('password')
                    if pw:
                        user.set_password(pw)
                    user.save()
                    
                    if is_judge:
                        # Clear old programs and add new ones
                        user.assigned_programs.clear()
                        programs = form.cleaned_data['assigned_programs']
                        for prog in programs:
                            prog.judges.add(user)
                            
                messages.success(request, f"User '{user.username}' updated successfully.")
                return redirect('/admin-panel/settings/?tab=users')
            except Exception as e:
                messages.error(request, f"Error: {e}")
    else:
        form = UserEditForm(user_instance=user, is_judge=is_judge)
    return render(request, 'programs/generic_form.html', {'form': form, 'action': 'Edit', 'type': 'User'})

@role_required('admin')
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        username = user.username
        # If teamlead, set team lead to Null
        if hasattr(user, 'userprofile') and user.userprofile.role == 'teamlead':
            from participants.models import Team
            Team.objects.filter(teamlead=user).update(teamlead=None)
        user.delete()
        messages.success(request, f"User '{username}' deleted.")
        return redirect('/admin-panel/settings/?tab=users')
    return render(request, 'programs/confirm_delete.html', {'obj': user, 'type': 'User'})


@role_required('admin')
def judge_assignment_list(request):
    programs = Program.objects.select_related('category').prefetch_related('judges').all()
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '').strip()
    if q:
        programs = programs.filter(name__icontains=q)
    if cat:
        programs = programs.filter(category__id=cat)
    categories = Category.objects.all()
    return render(request, 'programs/judge_assignment_list.html', {
        'programs': programs,
        'categories': categories,
        'q': q,
        'selected_cat': cat
    })

@role_required('admin')
def judge_assignment_edit(request, program_id):
    program = get_object_or_404(Program, pk=program_id)
    from .forms import JudgeAssignmentForm
    form = JudgeAssignmentForm(request.POST or None, instance=program)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Judges assigned to '{program.name}'.")
        return redirect('judge_assignment_list')
    return render(request, 'programs/generic_form.html', {
        'form': form,
        'action': 'Assign Judges to',
        'type': program.name
    })


# ─────────────────────────────────────────────
#  REPORTS VIEWS
# ─────────────────────────────────────────────
@role_required('admin')
def reports_dashboard(request):
    results_count = Result.objects.count()
    members_count = Member.objects.count()
    marksheets_count = Marksheet.objects.count()
    programs_count = Program.objects.count()
    teams_count = Team.objects.count()
    
    return render(request, 'programs/reports_dashboard.html', {
        'results_count': results_count,
        'members_count': members_count,
        'marksheets_count': marksheets_count,
        'programs_count': programs_count,
        'teams_count': teams_count,
    })

@role_required('admin')
def report_results(request):
    program_filter = request.GET.get('program', '').strip()
    category_filter = request.GET.get('category', '').strip()
    
    programs = Program.objects.select_related('category').all().order_by('name')
    categories = Category.objects.all().order_by('name')
    
    if category_filter:
        programs = programs.filter(category_id=category_filter)
        
    if program_filter:
        program = get_object_or_404(Program, id=program_filter)
        results = Result.objects.filter(program=program).select_related('member', 'member__team').order_by('rank')
        
        return render(request, 'programs/report_results_detail.html', {
            'program': program,
            'results': results,
            'selected_category': category_filter,
        })
    else:
        for p in programs:
            p.has_results = p.results.exists()
            p.is_published = p.results.filter(published=True).exists()
            p.results_count = p.results.count()
            
        return render(request, 'programs/report_results.html', {
            'programs': programs,
            'categories': categories,
            'selected_category': category_filter,
        })

@role_required('admin')
def report_members(request):
    team_filter = request.GET.get('team', '').strip()
    category_filter = request.GET.get('category', '').strip()
    
    members = Member.objects.select_related('team', 'category').prefetch_related('registered_programs').all().order_by('team__name', 'chest_no')
    
    if team_filter:
        members = members.filter(team_id=team_filter)
    if category_filter:
        members = members.filter(category_id=category_filter)
        
    teams = Team.objects.all().order_by('name')
    categories = Category.objects.all().order_by('name')
    
    return render(request, 'programs/report_members.html', {
        'members': members,
        'teams': teams,
        'categories': categories,
        'selected_team': team_filter,
        'selected_category': category_filter,
    })

@role_required('admin')
def report_marksheets(request):
    program_filter = request.GET.get('program', '').strip()
    category_filter = request.GET.get('category', '').strip()
    judge_filter = request.GET.get('judge', '').strip()
    status_filter = request.GET.get('status', '').strip()
    
    programs = Program.objects.select_related('category').all().order_by('name')
    categories = Category.objects.all().order_by('name')
    judges = User.objects.filter(userprofile__role='judge').order_by('username')
    
    if category_filter:
        programs = programs.filter(category_id=category_filter)
        
    if program_filter:
        program = get_object_or_404(Program, id=program_filter)
        sheets = Marksheet.objects.filter(program=program).select_related('member', 'member__team', 'judge').order_by('judge__username', 'member__name')
        
        if judge_filter:
            sheets = sheets.filter(judge_id=judge_filter)
        if status_filter == 'submitted':
            sheets = sheets.filter(submitted=True)
        elif status_filter == 'draft':
            sheets = sheets.filter(submitted=False)
            
        for s in sheets:
            raw = s.marks
            if isinstance(raw, dict):
                try:
                    s.total_score = sum(float(v) for v in raw.values() if str(v).replace('.', '', 1).isdigit())
                except Exception:
                    s.total_score = 0
            else:
                try:
                    s.total_score = float(raw)
                except (TypeError, ValueError):
                    s.total_score = 0
                    
        return render(request, 'programs/report_marksheets_detail.html', {
            'program': program,
            'sheets': sheets,
            'judges': judges,
            'selected_judge': judge_filter,
            'selected_status': status_filter,
            'selected_category': category_filter,
        })
    else:
        for p in programs:
            p.total_sheets = p.marksheets.count()
            p.submitted_sheets = p.marksheets.filter(submitted=True).count()
            p.pending_sheets = p.total_sheets - p.submitted_sheets
            
        return render(request, 'programs/report_marksheets.html', {
            'programs': programs,
            'categories': categories,
            'selected_category': category_filter,
        })

@role_required('admin')
def report_schedule(request):
    category_filter = request.GET.get('category', '').strip()
    venue_filter = request.GET.get('venue', '').strip()
    
    programs_qs = Program.objects.select_related('category').annotate(
        registrations=Count('registered_members')
    ).all().order_by('schedule', 'venue', 'name')
    
    if category_filter:
        programs_qs = programs_qs.filter(category_id=category_filter)
    if venue_filter:
        programs_qs = programs_qs.filter(venue__icontains=venue_filter)
        
    categories = Category.objects.all().order_by('name')
    
    # Get unique venues
    venues = Program.objects.exclude(venue='').values_list('venue', flat=True).distinct().order_by('venue')
    
    return render(request, 'programs/report_schedule.html', {
        'programs': programs_qs,
        'categories': categories,
        'venues': venues,
        'selected_category': category_filter,
        'selected_venue': venue_filter,
    })

@role_required('admin')
def report_teampoints(request):
    from results.utils import recalculate_team_points
    recalculate_team_points()
    
    team_points = TeamPoints.objects.select_related('team').all().order_by('-total_points')
    
    for tp in team_points:
        tp.breakdown_list = []
        if isinstance(tp.breakdown, dict):
            for prog_name, winners in tp.breakdown.items():
                for w in winners:
                    tp.breakdown_list.append({
                        'program': prog_name,
                        'member': w.get('member'),
                        'rank': w.get('rank'),
                        'points': w.get('pts')
                    })
        tp.breakdown_list.sort(key=lambda x: x['program'])
        
    return render(request, 'programs/report_teampoints.html', {
        'team_points': team_points,
    })


