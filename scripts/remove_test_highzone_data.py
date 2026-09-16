import os
import sys
import json
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'festalchemy.settings')
django.setup()

from django.core.cache import cache
from programs.models import Program
from participants.models import Member
from results.models import Result
from results.utils import recalculate_team_points

def main():
    ids_path = os.path.join(os.path.dirname(__file__), 'test_highzone_ids.json')
    if not os.path.exists(ids_path):
        print("No test_highzone_ids.json tracking file found. Searching by name prefix...")
        results_deleted = Result.objects.filter(program__name__startswith='High Zone').delete()
        progs_deleted = Program.objects.filter(name__startswith='High Zone').delete()
        members_deleted = Member.objects.filter(category__name='High Zone').delete()
    else:
        with open(ids_path, 'r') as f:
            data = json.load(f)

        results_deleted = Result.objects.filter(id__in=data.get('result_ids', [])).delete()
        progs_deleted = Program.objects.filter(id__in=data.get('program_ids', [])).delete()
        members_deleted = Member.objects.filter(id__in=data.get('member_ids', [])).delete()
        try:
            os.remove(ids_path)
        except Exception:
            pass

    recalculate_team_points()
    cache.delete('public_dashboard_stats')
    cache.delete('admin_bootstrap_data')
    cache.delete('admin_dashboard_stats')

    print(f"Removed test data: Results: {results_deleted}, Programs: {progs_deleted}, Members: {members_deleted}")
    print("Team points recalculated and cache cleared.")

if __name__ == '__main__':
    main()
