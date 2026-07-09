from django.shortcuts import render, get_object_or_404
from django.db.models import Sum
from programs.models import Program
from participants.models import Team, Member
from judging.models import Marksheet
from .models import Result, TeamPoints

def home(request):
    programs = Program.objects.all().order_by('schedule')
    
    # Programs with published results
    published_program_ids = Result.objects.filter(published=True).values_list('program_id', flat=True).distinct()
    programs_with_results = Program.objects.filter(id__in=published_program_ids).order_by('-schedule')

    # Team leaderboard — ordered by total points
    team_points = TeamPoints.objects.select_related('team').order_by('-total_points')

    # Individual member points: sum total_marks from published results per member (only counting program__type='single')
    from django.db.models import Count
    member_points = (
        Result.objects.filter(published=True, program__type='single')
        .values('member__id', 'member__name', 'member__team__name')
        .annotate(total=Sum('points'), events=Count('id'))
        .order_by('-total')[:20]  # top 20
    )

    return render(request, 'results/home.html', {
        'programs': programs,
        'programs_with_results': programs_with_results,
        'team_points': team_points,
        'member_points': member_points,
    })

def program_results(request, program_id):
    program = get_object_or_404(Program, id=program_id)
    qs = Result.objects.filter(program=program, published=True).order_by('rank')
    
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
            
    return render(request, 'results/program_results.html', {
        'program': program,
        'results': results_list
    })
