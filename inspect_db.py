import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'festalchemy.settings')
django.setup()

from django.contrib.auth.models import User
from programs.models import FestSettings, Category, Program, ProgramGradeSetting
from participants.models import Team, Member, CallingList
from results.models import Result, TeamPoints
from accounts.models import UserProfile

print("=== USERS & ROLES ===")
for u in User.objects.all():
    profile = getattr(u, 'userprofile', None)
    role = profile.role if profile else "No Profile"
    team = profile.team.name if profile and profile.team else "No Team"
    print(f"- {u.username} (Email: {u.email}, Role: {role}, Team: {team})")

print("\n=== MEMBERS ===")
for m in Member.objects.all():
    print(f"- {m.name} (Chest: {m.chest_no}, Category: {m.category.name}, Team: {m.team.name})")
    print(f"  Registered Programs: {[p.name for p in m.registered_programs.all()]}")

print("\n=== PROGRAMS & JUDGES ===")
for p in Program.objects.all():
    print(f"- {p.name} ({p.category.name}, Type: {p.type}, Max Marks: {p.max_marks})")
    print(f"  Judges: {[u.username for u in p.judges.all()]}")

print("\n=== GRADE SETTINGS ===")
for g in ProgramGradeSetting.objects.all():
    print(f"- {g.program.name}: {g.grade_name} (>= {g.min_marks} marks, points: {g.points})")
