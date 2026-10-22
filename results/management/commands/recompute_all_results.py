from django.core.management.base import BaseCommand
from django.db import transaction
from programs.models import Program
from results.models import Result
from results.scoring import determine_grade, calculate_result_points
from results.utils import recalculate_team_points

class Command(BaseCommand):
    help = 'Recompute all ranks, grades, and points across all programs using the updated grading system'

    def handle(self, *args, **options):
        programs_with_results = Program.objects.filter(results__isnull=False).distinct()
        total_programs = programs_with_results.count()
        self.stdout.write(f"Found {total_programs} programs with existing results.")

        total_results_updated = 0
        with transaction.atomic():
            for program in programs_with_results:
                results = list(Result.objects.filter(program=program).select_related('member'))
                if not results:
                    continue

                # Sort by total_marks descending
                results.sort(key=lambda r: r.total_marks, reverse=True)
                grade_rules = list(program.grade_settings.all())

                current_rank = 0
                prev_marks = None
                for r in results:
                    rounded_marks = round(r.total_marks, 2)
                    if prev_marks is None or rounded_marks != prev_marks:
                        current_rank += 1
                    prev_marks = rounded_marks
                    r.rank = current_rank

                    scaled = (r.total_marks / program.max_marks) * 100 if program.max_marks > 0 else r.total_marks
                    r.grade = determine_grade(scaled, custom_grade_rules=grade_rules)
                    r.points = calculate_result_points(
                        grade_name=r.grade,
                        rank=r.rank,
                        program_type=program.type,
                        custom_grade_rules=grade_rules
                    )

                Result.objects.bulk_update(results, ['rank', 'grade', 'points'])
                total_results_updated += len(results)
                self.stdout.write(f"  ✓ Updated {len(results)} results for program: {program.name}")

        self.stdout.write("Recalculating team points leaderboard...")
        recalculate_team_points()

        self.stdout.write(self.style.SUCCESS(
            f"Successfully recomputed {total_results_updated} results across {total_programs} programs."
        ))
