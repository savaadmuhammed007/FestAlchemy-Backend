import os
import sys
import json
import random
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'festalchemy.settings')
django.setup()

from django.core.cache import cache
from programs.models import Category, Program, FestSettings
from participants.models import Team, Member, CallingList
from results.models import Result
from results.utils import recalculate_team_points

def main():
    print("Setting up High Zone test data...")
    high_zone = Category.objects.get(name='High Zone')
    fest = FestSettings.objects.first()

    teams = list(Team.objects.all())
    if not teams:
        print("Error: No teams found!")
        return

    team_horizon = Team.objects.filter(name__icontains='Horizon').first() or teams[0]
    team_heritage = Team.objects.filter(name__icontains='Heritage').first() or (teams[1] if len(teams) > 1 else teams[0])

    created_ids = {
        'program_ids': [],
        'member_ids': [],
        'result_ids': [],
    }

    # 1. Create 5 Participants in High Zone
    participant_data = [
        ("Zayan Ahmed", team_horizon),
        ("Nihal Rayan", team_heritage),
        ("Ameen Bilal", team_horizon),
        ("Faheem Shakir", team_heritage),
        ("Hassan Farhan", team_horizon),
    ]

    members = []
    start_chest = (high_zone.chest_prefix or 300) + 1
    for name, team in participant_data:
        # Check if member already exists
        m = Member.objects.filter(name=name, category=high_zone).first()
        if not m:
            m = Member(
                name=name,
                team=team,
                category=high_zone,
                chest_no=start_chest
            )
            m.save()
            start_chest += 1
        members.append(m)
        created_ids['member_ids'].append(m.id)

    print(f"Created/found {len(members)} High Zone participants: {[m.name for m in members]}")

    # 2. Create 4 Programs in High Zone
    program_names = [
        ("High Zone English Elocution", "single", "onstage"),
        ("High Zone Extempore Speech", "single", "onstage"),
        ("High Zone Essay Writing", "single", "offstage"),
        ("High Zone Pencil Drawing", "single", "offstage"),
    ]

    programs = []
    for p_name, p_type, s_type in program_names:
        prog, _ = Program.objects.get_or_create(
            name=p_name,
            category=high_zone,
            defaults={
                'fest': fest,
                'type': p_type,
                'stage_type': s_type,
                'duration': 7,
                'max_marks': 100,
            }
        )
        # Register all 5 members
        prog.registered_members.set(members)
        programs.append(prog)
        created_ids['program_ids'].append(prog.id)

    print(f"Created {len(programs)} High Zone programs: {[p.name for p in programs]}")

    # 3. Add random verified marks and published results
    point_map = fest.point_system if fest and fest.point_system else {'1st': 3, '2nd': 2, '3rd': 1}
    ranks_meta = [
        (1, point_map.get('1st', 3), 'A+'),
        (2, point_map.get('2nd', 2), 'A'),
        (3, point_map.get('3rd', 1), 'B+'),
        (4, 0, 'B'),
        (5, 0, 'C'),
    ]

    for prog in programs:
        # Shuffle members for varied winners across programs
        shuffled = list(members)
        random.shuffle(shuffled)

        # Clear any existing test results for this program
        Result.objects.filter(program=prog).delete()

        base_mark = random.uniform(92.0, 97.0)
        for i, member in enumerate(shuffled):
            rank, pts, grade = ranks_meta[i]
            mark = round(base_mark - (i * random.uniform(2.5, 4.5)), 1)
            res = Result.objects.create(
                program=prog,
                member=member,
                total_marks=mark,
                rank=rank,
                points=pts,
                grade=grade,
                judge_code=f"J{random.randint(101, 109)}",
                published=True
            )
            created_ids['result_ids'].append(res.id)

    # 4. Save IDs to file for easy one-click removal later
    ids_path = os.path.join(os.path.dirname(__file__), 'test_highzone_ids.json')
    with open(ids_path, 'w') as f:
        json.dump(created_ids, f, indent=2)

    # 5. Recalculate standings and flush cache
    recalculate_team_points()
    cache.delete('public_dashboard_stats')
    cache.delete('admin_bootstrap_data')
    cache.delete('admin_dashboard_stats')

    print("Success! 4 High Zone programs, 5 participants, and published results have been added.")
    print(f"Tracking file written to: {ids_path}")

if __name__ == '__main__':
    main()
