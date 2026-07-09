from django.shortcuts import render, redirect, get_object_or_404
from accounts.decorators import role_required
from .models import Member, Team
from .forms import MemberForm
from programs.models import Program, Category
from django.contrib import messages
from django.db.models import Count, Q, F


def _get_team(user):
    """Return the Team where this user is the teamlead (primary source of truth)."""
    team = Team.objects.filter(teamlead=user).first()
    if not team:
        # Fallback: check UserProfile.team if admin assigned it manually
        try:
            team = user.userprofile.team
        except Exception:
            pass
    return team


@role_required('teamlead')
def teamlead_dashboard(request):
    team = _get_team(request.user)
    if not team:
        messages.error(request, "You are not assigned to any team. Please ask the Admin to create a team and assign you as its Team Lead.")
        return render(request, 'participants/no_team.html')

    members = Member.objects.filter(team=team).select_related('category')
    return render(request, 'participants/teamlead_dashboard.html', {
        'team': team,
        'members': members,
    })


@role_required('teamlead')
def add_member(request):
    team = _get_team(request.user)
    if not team:
        messages.error(request, "No team assigned. Contact Admin.")
        return redirect('teamlead_dashboard')

    # Pre-fetch programs that are not full FOR THIS TEAM
    from programs.models import Program
    all_programs = Program.objects.select_related('category').annotate(
        team_count=Count('registered_members', filter=Q(registered_members__team=team))
    ).filter(
        Q(participant_limit=0) | Q(team_count__lt=F('participant_limit'))
    )

    # Build a dict of {category_id: [program, …]} to pass as JSON for JS
    import json
    from collections import defaultdict
    programs_by_cat = defaultdict(list)
    
    general_cat = Category.objects.filter(name__iexact='general').first()
    general_programs = []
    category_programs = defaultdict(list)
    
    for p in all_programs:
        if general_cat and p.category_id == general_cat.id:
            general_programs.append({'id': p.id, 'name': p.name})
        else:
            category_programs[p.category_id].append({'id': p.id, 'name': p.name})
            
    all_cat_ids = set(Category.objects.values_list('id', flat=True))
    for cat_id in all_cat_ids:
        programs_by_cat[cat_id] = category_programs[cat_id] + general_programs
        
    if general_cat:
        programs_by_cat[general_cat.id] = general_programs

    programs_by_cat_json = json.dumps(programs_by_cat)

    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.team = team
            member.save()
            # Assign selected programs
            program_ids = request.POST.getlist('programs')
            if program_ids:
                member.registered_programs.set(program_ids)
            messages.success(request, f"Member added. Chest No {member.chest_no} assigned.")
            return redirect('teamlead_dashboard')
    else:
        form = MemberForm()

    return render(request, 'participants/add_member.html', {
        'form': form,
        'programs_by_cat_json': programs_by_cat_json,
    })


@role_required('teamlead')
def assign_program(request, member_id):
    team = _get_team(request.user)
    member = get_object_or_404(Member, id=member_id, team=team)

    member_program_ids = list(member.registered_programs.values_list('id', flat=True))
    general_cat = Category.objects.filter(name__iexact='general').first()
    if general_cat and general_cat != member.category:
        program_filter = Q(category=member.category) | Q(category=general_cat)
    else:
        program_filter = Q(category=member.category)

    available_programs = Program.objects.filter(program_filter).annotate(
        team_count=Count('registered_members', filter=Q(registered_members__team=team))
    ).filter(
        Q(participant_limit=0) | Q(team_count__lt=F('participant_limit')) | Q(id__in=member_program_ids)
    )

    if request.method == 'POST':
        program_ids = request.POST.getlist('programs')
        member.registered_programs.set(program_ids)
        messages.success(request, f"Programs updated for {member.name}.")
        return redirect('teamlead_dashboard')

    return render(request, 'participants/assign_program.html', {
        'member': member,
        'available_programs': available_programs,
        'registered_ids': list(member.registered_programs.values_list('id', flat=True))
    })
