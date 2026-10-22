import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'festalchemy.settings')
django.setup()

from results.models import Result
from results.scoring import determine_grade, calculate_result_points
from results.utils import recalculate_team_points

print("Updating results with updated grade and points system...")
count = 0
for r in Result.objects.select_related('program').all():
    program = r.program
    scaled = (r.total_marks / program.max_marks) * 100 if program.max_marks > 0 else r.total_marks
    grade_rules = list(program.grade_settings.all())
    
    new_grade = determine_grade(scaled, custom_grade_rules=grade_rules)
    new_points = calculate_result_points(
        grade_name=new_grade,
        rank=r.rank,
        program_type=program.type,
        custom_grade_rules=grade_rules
    )
    
    if r.grade != new_grade or r.points != new_points:
        r.grade = new_grade
        r.points = new_points
        r.save(update_fields=['grade', 'points'])
        count += 1

recalculate_team_points()
print(f"Done. Updated {count} results and recalculated team standings.")
