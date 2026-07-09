import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'festalchemy.settings')
django.setup()

from results.models import Result
from programs.models import FestSettings

fest = FestSettings.objects.first()
point_map = fest.point_system if fest else {}

print(f"Updating results with points system: {point_map}")
count = 0
for r in Result.objects.all():
    rank_key = {1: '1st', 2: '2nd', 3: '3rd'}.get(r.rank)
    old_points = r.points
    r.points = point_map.get(rank_key, 0) if rank_key else 0
    if old_points != r.points:
        r.save()
        count += 1

print(f"Done. Updated {count} results.")
