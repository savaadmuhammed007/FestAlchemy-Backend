from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count, Q, F, Sum
import json
import random

# Models
from accounts.models import UserProfile
from programs.models import FestSettings, Category, Program, PosterTemplate, GlobalPosterTemplate, ProgramGradeSetting, Stage
from participants.models import Team, Member, CallingList
from judging.models import Marksheet
from results.models import Result, TeamPoints

# Serializers
from accounts.serializers import UserSerializer, UserProfileSerializer
from programs.serializers import FestSettingsSerializer, CategorySerializer, ProgramSerializer, ProgramGradeSettingSerializer, PosterTemplateSerializer, GlobalPosterTemplateSerializer, StageSerializer
from participants.serializers import TeamSerializer, MemberSerializer, CallingListSerializer
from judging.serializers import MarksheetSerializer
from results.serializers import ResultSerializer, TeamPointsSerializer

# Permissions
class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'admin'

class IsJudgeRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'judge'

class IsTeamLeadRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'teamlead'

class ReadOnlyOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'admin'

# ────────────────────────────────────────────────────────
#  AUTHENTICATION APIS
# ────────────────────────────────────────────────────────
class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response({'error': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(username=username, password=password)
        if not user:
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_400_BAD_REQUEST)
        
        token, _ = Token.objects.get_or_create(user=user)
        
        # Profile details
        role = 'user'
        team_id = None
        team_name = None
        if hasattr(user, 'userprofile'):
            role = user.userprofile.role
            if user.userprofile.team:
                team_id = user.userprofile.team.id
                team_name = user.userprofile.team.name
        
        # If teamlead role, find team lead relation
        if role == 'teamlead' and not team_id:
            team_obj = Team.objects.filter(teamlead=user).first()
            if team_obj:
                team_id = team_obj.id
                team_name = team_obj.name

        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': role,
                'team_id': team_id,
                'team_name': team_name
            }
        })

class LogoutAPIView(APIView):
    def post(self, request):
        request.user.auth_token.delete()
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)

class MeAPIView(APIView):
    def get(self, request):
        user = request.user
        role = 'user'
        team_id = None
        team_name = None
        if hasattr(user, 'userprofile'):
            role = user.userprofile.role
            if user.userprofile.team:
                team_id = user.userprofile.team.id
                team_name = user.userprofile.team.name
        
        if role == 'teamlead' and not team_id:
            team_obj = Team.objects.filter(teamlead=user).first()
            if team_obj:
                team_id = team_obj.id
                team_name = team_obj.name

        return Response({
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': role,
            'team_id': team_id,
            'team_name': team_name
        })

# ────────────────────────────────────────────────────────
#  CRUD VIEWSETS
# ────────────────────────────────────────────────────────

class FestSettingsViewSet(viewsets.ModelViewSet):
    queryset = FestSettings.objects.all()
    serializer_class = FestSettingsSerializer
    permission_classes = [ReadOnlyOrAdmin]

    def get_queryset(self):
        return FestSettings.objects.all()

class StageViewSet(viewsets.ModelViewSet):
    queryset = Stage.objects.all()
    serializer_class = StageSerializer
    permission_classes = [ReadOnlyOrAdmin]

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [ReadOnlyOrAdmin]

    def get_queryset(self):
        # Auto-create General category if it doesn't exist
        if not Category.objects.filter(name__iexact='general').exists():
            from django.db.models import Max
            max_prefix = Category.objects.all().aggregate(Max('chest_prefix'))['chest_prefix__max']
            prefix = (max_prefix + 100) if max_prefix is not None else 900
            Category.objects.create(name='General', chest_prefix=prefix)
        return Category.objects.all().order_by('id')

class ProgramGradeSettingViewSet(viewsets.ModelViewSet):
    queryset = ProgramGradeSetting.objects.all()
    serializer_class = ProgramGradeSettingSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        qs = self.queryset
        program_id = self.request.query_params.get('program')
        if program_id:
            qs = qs.filter(program_id=program_id)
        return qs

class ProgramViewSet(viewsets.ModelViewSet):
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
    permission_classes = [ReadOnlyOrAdmin]

    def get_queryset(self):
        qs = Program.objects.all().order_by('schedule')
        user = self.request.user
        judge_only = self.request.query_params.get('judge_only')
        if judge_only == 'true' and user.is_authenticated:
            qs = qs.filter(judges=user)
        return qs

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=False, methods=['post'], permission_classes=[IsAdminRole])
    def auto_schedule(self, request):
        start_time_str = request.data.get('start_time', '09:00')
        end_time_str = request.data.get('end_time', '17:00')
        interval_between = int(request.data.get('interval_between', 5))
        reschedule_all = request.data.get('reschedule_all', False)
        target_day = request.data.get('target_day', 'all')
        program_ids = request.data.get('program_ids', [])

        # Parse start and end times
        try:
            start_h, start_m = map(int, start_time_str.split(':'))
            end_h, end_m = map(int, end_time_str.split(':'))
        except Exception:
            return Response({'error': 'Invalid start_time or end_time format (expected HH:MM)'}, status=status.HTTP_400_BAD_REQUEST)

        # Get fest settings and dates
        fest = FestSettings.objects.first()
        if not fest or not fest.dates:
            return Response({'error': 'Please configure Fest Dates in Fest Settings before auto-scheduling.'}, status=status.HTTP_400_BAD_REQUEST)

        fest_dates = fest.dates

        # Get onstage and offstage stages
        stages = list(Stage.objects.all())
        onstage_stages = [stg.name for stg in stages if stg.type == 'onstage']
        offstage_stages = [stg.name for stg in stages if stg.type == 'offstage']

        if not onstage_stages:
            onstage_stages = ['Stage 1']
        if not offstage_stages:
            offstage_stages = ['Offstage Stage']

        # Get programs
        programs_qs = Program.objects.all().order_by('category__name', 'name')
        if program_ids:
            programs_qs = programs_qs.filter(id__in=program_ids)
        elif not reschedule_all:
            programs_qs = programs_qs.filter(schedule=None)

        programs_list = list(programs_qs)
        if not programs_list:
            return Response({'message': 'No programs to schedule.'})

        onstage_programs = [p for p in programs_list if p.stage_type == 'onstage']
        offstage_programs = [p for p in programs_list if p.stage_type == 'offstage']

        # Distribute onstage programs to onstage stages round-robin
        onstage_stage_programs = {name: [] for name in onstage_stages}
        for idx, p in enumerate(onstage_programs):
            s_name = onstage_stages[idx % len(onstage_stages)]
            onstage_stage_programs[s_name].append(p)

        # Distribute offstage programs to offstage stages round-robin
        offstage_stage_programs = {name: [] for name in offstage_stages}
        for idx, p in enumerate(offstage_programs):
            s_name = offstage_stages[idx % len(offstage_stages)]
            offstage_stage_programs[s_name].append(p)

        # Merge distributions
        all_stage_programs = {}
        all_stage_programs.update(onstage_stage_programs)
        all_stage_programs.update(offstage_stage_programs)

        import datetime
        from django.utils import timezone
        
        updated_programs = []

        for stage_name, progs in all_stage_programs.items():
            if target_day == 'all':
                current_day_idx = 0
            else:
                try:
                    current_day_idx = int(target_day)
                    if current_day_idx < 0 or current_day_idx >= len(fest_dates):
                        return Response({'error': f'Target day index out of bounds (0-{len(fest_dates)-1})'}, status=status.HTTP_400_BAD_REQUEST)
                except ValueError:
                    return Response({'error': 'Invalid target_day value (expected "all" or integer index)'}, status=status.HTTP_400_BAD_REQUEST)
            
            def get_datetime_cursor(day_idx, hour, minute):
                date_str = fest_dates[day_idx]
                dt = datetime.datetime.strptime(f"{date_str} {hour:02d}:{minute:02d}", "%Y-%m-%d %H:%M")
                return timezone.make_aware(dt)

            current_time = get_datetime_cursor(current_day_idx, start_h, start_m)

            for p in progs:
                reg_count = p.registered_members.count()
                p_duration = p.duration if p.stage_type == 'offstage' else p.duration * reg_count
                p_duration = max(5, p_duration)

                day_end_time = get_datetime_cursor(current_day_idx, end_h, end_m)
                
                # Roll over to next day only if target_day is 'all'
                if target_day == 'all':
                    if current_time + datetime.timedelta(minutes=p_duration) > day_end_time:
                        current_day_idx += 1
                        if current_day_idx < len(fest_dates):
                            current_time = get_datetime_cursor(current_day_idx, start_h, start_m)
                        else:
                            current_time = get_datetime_cursor(len(fest_dates) - 1, start_h, start_m) + datetime.timedelta(days=current_day_idx - (len(fest_dates) - 1))
                
                p.schedule = current_time
                p.venue = stage_name
                p.save()
                updated_programs.append(p)

                current_time = current_time + datetime.timedelta(minutes=p_duration + interval_between)

        serializer = ProgramSerializer(updated_programs, many=True)
        return Response({
            'message': f'Successfully scheduled {len(updated_programs)} programs.',
            'programs': serializer.data
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAdminRole])
    def reset_schedule(self, request):
        programs = Program.objects.all()
        count = programs.count()
        programs.update(schedule=None, venue='')
        return Response({
            'message': f'All program schedules and venues have been successfully reset for {count} programs.'
        })

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsAdminRole])
    def grade_settings(self, request, pk=None):
        program = self.get_object()
        if request.method == 'GET':
            rules = program.grade_settings.all()
            serializer = ProgramGradeSettingSerializer(rules, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            # Create a grade setting rule
            grade_name = request.data.get('grade_name')
            min_marks = request.data.get('min_marks')
            points = request.data.get('points', 0)
            
            if not grade_name or min_marks is None:
                return Response({'error': 'grade_name and min_marks are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                min_marks = float(min_marks)
                points = int(points)
            except ValueError:
                return Response({'error': 'Invalid min_marks or points values.'}, status=status.HTTP_400_BAD_REQUEST)

            if min_marks < 0 or min_marks > program.max_marks:
                return Response({'error': f'Minimum marks must be between 0 and {program.max_marks}.'}, status=status.HTTP_400_BAD_REQUEST)

            rule, created = ProgramGradeSetting.objects.get_or_create(
                program=program,
                grade_name=grade_name,
                defaults={'min_marks': min_marks, 'points': points}
            )
            if not created:
                rule.min_marks = min_marks
                rule.points = points
                rule.save()

            serializer = ProgramGradeSettingSerializer(rule)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminRole])
    def delete_grade_setting(self, request, pk=None):
        program = self.get_object()
        rule_id = request.data.get('rule_id')
        rule = get_object_or_404(ProgramGradeSetting, id=rule_id, program=program)
        rule.delete()
        return Response({'status': 'deleted'})

class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [ReadOnlyOrAdmin]

    @action(detail=False, methods=['post'], permission_classes=[IsAdminRole])
    def register_team_lead(self, request):
        from django.contrib.auth.models import User
        username = request.data.get('username')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        team_name = request.data.get('team_name')

        if not username or not password or not team_name:
            return Response({'error': 'Username, password and team_name are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        if Team.objects.filter(name=team_name).exists():
            return Response({'error': 'Team name already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            new_user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            UserProfile.objects.update_or_create(
                user=new_user,
                defaults={'role': 'teamlead'}
            )
            team = Team.objects.create(name=team_name, teamlead=new_user)
            
            # Sync team lead profile
            profile = new_user.userprofile
            profile.team = team
            profile.save()

        serializer = TeamSerializer(team)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = user.userprofile.role if hasattr(user, 'userprofile') else 'user'
        
        if role == 'teamlead':
            # Team leads can only see/manage members of their own team
            team = Team.objects.filter(teamlead=user).first()
            if not team and user.userprofile.team:
                team = user.userprofile.team
            if team:
                return Member.objects.filter(team=team)
            return Member.objects.none()
        
        # Admins, Judges, Public can see all members
        qs = Member.objects.all()
        
        team_id = self.request.query_params.get('team')
        category_id = self.request.query_params.get('category')
        if team_id:
            qs = qs.filter(team_id=team_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        role = user.userprofile.role if hasattr(user, 'userprofile') else 'user'
        if role == 'teamlead':
            team = Team.objects.filter(teamlead=user).first()
            if not team and user.userprofile.team:
                team = user.userprofile.team
            if not team:
                raise serializers.ValidationError("No team assigned to this team lead.")
            serializer.save(team=team)
        else:
            serializer.save()

    @action(detail=False, methods=['get'])
    def team_programs_availability(self, request):
        # Helper to get programs and indicate which ones have slots left for the teamlead's team
        user = request.user
        team = Team.objects.filter(teamlead=user).first()
        if not team and hasattr(user, 'userprofile'):
            team = user.userprofile.team
        if not team:
            return Response({'error': 'No team assigned.'}, status=status.HTTP_400_BAD_REQUEST)
        
        category_id = request.query_params.get('category')
        qs = Program.objects.all()
        if category_id:
            general_cat = Category.objects.filter(name__iexact='general').first()
            if general_cat and str(general_cat.id) != str(category_id):
                qs = qs.filter(Q(category_id=category_id) | Q(category_id=general_cat.id))
            else:
                qs = qs.filter(category_id=category_id)

        all_programs = qs.select_related('category').annotate(
            team_count=Count('registered_members', filter=Q(registered_members__team=team))
        )

        data = []
        for p in all_programs:
            has_slot = (p.participant_limit == 0 or p.team_count < p.participant_limit)
            data.append({
                'id': p.id,
                'name': p.name,
                'category_id': p.category.id,
                'category_name': p.category.name,
                'participant_limit': p.participant_limit,
                'current_team_registered': p.team_count,
                'has_available_slot': has_slot,
                'type': p.type,
                'stage_type': p.stage_type
            })
        return Response(data)

class MarksheetViewSet(viewsets.ModelViewSet):
    queryset = Marksheet.objects.all()
    serializer_class = MarksheetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = user.userprofile.role if hasattr(user, 'userprofile') else 'user'
        
        if role == 'judge':
            # Judges can only see marksheets assigned to them
            qs = Marksheet.objects.filter(judge=user)
            program_id = self.request.query_params.get('program')
            if program_id:
                qs = qs.filter(program_id=program_id)
            return qs
        elif role == 'admin':
            # Admin can see all
            qs = Marksheet.objects.all()
            program_id = self.request.query_params.get('program')
            if program_id:
                qs = qs.filter(program_id=program_id)
            return qs
        
        return Marksheet.objects.none()

    @action(detail=True, methods=['post'])
    def evaluate(self, request, pk=None):
        marksheet = self.get_object()
        
        # Ensure only the assigned judge can evaluate
        if marksheet.judge != request.user and request.user.userprofile.role != 'admin':
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            
        if marksheet.submitted:
            return Response({'error': 'This marksheet has already been submitted.'}, status=status.HTTP_400_BAD_REQUEST)

        score = request.data.get('score')
        submit = request.data.get('submit', False)

        if score is None:
            return Response({'error': 'score is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            score_val = float(score)
        except (TypeError, ValueError):
            return Response({'error': 'score must be a numeric value.'}, status=status.HTTP_400_BAD_REQUEST)

        if score_val < 0 or score_val > marksheet.program.max_marks:
            return Response({'error': f'score must be between 0 and {marksheet.program.max_marks}.'}, status=status.HTTP_400_BAD_REQUEST)

        marksheet.marks = {'total': score_val}
        if submit:
            marksheet.submitted = True
        marksheet.save()

        serializer = MarksheetSerializer(marksheet)
        return Response(serializer.data)

class ResultViewSet(viewsets.ModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    permission_classes = [ReadOnlyOrAdmin]

    def get_queryset(self):
        qs = Result.objects.all().order_by('rank')
        program_id = self.request.query_params.get('program')
        published_only = self.request.query_params.get('published_only')
        
        if program_id:
            qs = qs.filter(program_id=program_id)
        if published_only == 'true':
            qs = qs.filter(published=True)
            
        return qs

    def perform_update(self, serializer):
        instance = serializer.save()
        if 'total_marks' in serializer.validated_data:
            self.update_and_recalculate_rankings(instance.program)

    def perform_destroy(self, instance):
        program = instance.program
        instance.delete()
        self.update_and_recalculate_rankings(program)

    def update_and_recalculate_rankings(self, program):
        results = list(Result.objects.filter(program=program))
        results.sort(key=lambda r: r.total_marks, reverse=True)
        grade_rules = list(program.grade_settings.all())
        
        for r in results:
            scaled = (r.total_marks / program.max_marks) * 100 if program.max_marks > 0 else r.total_marks
            
            grade_name = None
            for rule in grade_rules:
                if scaled >= rule.min_marks:
                    grade_name = rule.grade_name
                    break
            
            if not grade_name:
                if scaled >= 95: grade_name = "A+"
                elif scaled >= 85: grade_name = "A"
                elif scaled >= 75: grade_name = "B"
                elif scaled >= 65: grade_name = "C"
                elif scaled >= 50: grade_name = "D"
            
            r.grade = grade_name
            
        grade_counts = {}
        for r in results:
            if r.grade:
                grade_counts[r.grade] = grade_counts.get(r.grade, 0) + 1
                
        with transaction.atomic():
            for rank_idx, r in enumerate(results, start=1):
                r.rank = rank_idx
                
                pts = 0
                if r.grade:
                    for rule in grade_rules:
                        if rule.grade_name == r.grade:
                            pts = rule.points
                            break
                
                if pts == 0 and r.grade:
                    if program.type == 'group':
                        if r.grade == "A+": pts = 20
                        elif r.grade == "A": pts = 15
                        elif r.grade == "B": pts = 10
                        elif r.grade == "C": pts = 5
                        elif r.grade == "D": pts = 3
                    else:
                        if r.grade == "A+": pts = 10
                        elif r.grade == "A": pts = 8
                        elif r.grade == "B": pts = 6
                        elif r.grade == "C": pts = 4
                        elif r.grade == "D": pts = 2
                
                if r.grade and grade_counts.get(r.grade, 0) > 1:
                    if rank_idx == 1:
                        pts += 3
                    elif rank_idx == 2:
                        pts += 1
                        
                r.points = pts
                r.save()
                
        from results.utils import recalculate_team_points
        recalculate_team_points()

    @action(detail=False, methods=['post'], permission_classes=[IsAdminRole])
    def compute(self, request):
        program_id = request.data.get('program_id')
        if not program_id:
            return Response({'error': 'program_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        program = get_object_or_404(Program, pk=program_id)

        sheets = Marksheet.objects.filter(program=program, submitted=True)

        if not sheets.exists():
            return Response({'error': 'No submitted marksheets found for this program.'}, status=status.HTTP_400_BAD_REQUEST)

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

        averaged = {mid: totals[mid] / counts[mid] for mid in totals}
        ranked = sorted(averaged.items(), key=lambda x: x[1], reverse=True)

        fest = FestSettings.objects.first()
        point_map = fest.point_system if fest else {}
        grade_rules = list(program.grade_settings.all())

        # Pre-compute entries, grades, and base points
        computed_entries = []
        for rank_idx, (member_id, avg_marks) in enumerate(ranked, start=1):
            scaled = (avg_marks / program.max_marks) * 100 if program.max_marks > 0 else avg_marks
            
            grade_name = None
            for rule in grade_rules:
                if scaled >= rule.min_marks:
                    grade_name = rule.grade_name
                    break
            
            if not grade_name:
                if scaled >= 95: grade_name = "A+"
                elif scaled >= 85: grade_name = "A"
                elif scaled >= 75: grade_name = "B"
                elif scaled >= 65: grade_name = "C"
                elif scaled >= 50: grade_name = "D"

            pts = 0
            if grade_name:
                for rule in grade_rules:
                    if rule.grade_name == grade_name:
                        pts = rule.points
                        break
            
            if pts == 0 and grade_name:
                if program.type == 'group':
                    if grade_name == "A+": pts = 20
                    elif grade_name == "A": pts = 15
                    elif grade_name == "B": pts = 10
                    elif grade_name == "C": pts = 5
                    elif grade_name == "D": pts = 3
                else:
                    if grade_name == "A+": pts = 10
                    elif grade_name == "A": pts = 8
                    elif grade_name == "B": pts = 6
                    elif grade_name == "C": pts = 4
                    elif grade_name == "D": pts = 2

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

        # Fetch and return computed results
        computed = Result.objects.filter(program=program).order_by('rank')
        serializer = ResultSerializer(computed, many=True)
        return Response({'message': f'Results computed for program {program.name}', 'data': serializer.data})

    @action(detail=False, methods=['post'], permission_classes=[IsAdminRole])
    def toggle_publish(self, request):
        program_id = request.data.get('program_id')
        if not program_id:
            return Response({'error': 'program_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        program = get_object_or_404(Program, id=program_id)
        results = program.results.all()
        if not results.exists():
            return Response({'error': 'No results found to publish.'}, status=status.HTTP_400_BAD_REQUEST)
        
        is_published = results.filter(published=True).exists()
        if is_published:
            results.update(published=False)
            message = f"Results for '{program.name}' hidden."
        else:
            results.update(published=True)
            message = f"Results for '{program.name}' published."

        from results.utils import recalculate_team_points
        recalculate_team_points()

        return Response({'message': message, 'published': not is_published})

class TeamPointsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TeamPoints.objects.all().order_by('-total_points')
    serializer_class = TeamPointsSerializer
    permission_classes = [permissions.AllowAny]

# ────────────────────────────────────────────────────────
#  SPECIALTY LOT SPINNING & CALLING APIS
# ────────────────────────────────────────────────────────

class LotCallingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, program_id):
        program = get_object_or_404(Program, id=program_id)
        CallingList.pregenerate_for_program(program)
        callings = CallingList.objects.filter(program=program).select_related('member')
        status_map = {c.member_id: c.status for c in callings}
        code_map = {c.member_id: c.calling_code.split('-')[1] if '-' in c.calling_code else c.calling_code for c in callings}
        
        members = list(program.registered_members.all())
        data = []
        for m in members:
            data.append({
                'id': m.id,
                'name': m.name,
                'chest_no': m.chest_no,
                'team_name': m.team.name,
                'called': status_map.get(m.id) == 'called',
                'judge_code': code_map.get(m.id, "??")
            })
        return Response({
            'program_name': program.name,
            'max_marks': program.max_marks,
            'members': data
        })

    def post(self, request, program_id):
        if not request.user.is_authenticated or not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'admin':
            return Response({'error': 'Admin permission required.'}, status=status.HTTP_403_FORBIDDEN)
            
        program = get_object_or_404(Program, id=program_id)
        if program.results.exists():
            return Response({'error': 'Cannot spin lot for a program with finalized results.'}, status=status.HTTP_400_BAD_REQUEST)
            
        CallingList.pregenerate_for_program(program)
        member_id = request.data.get('member_id')
        if not member_id:
            return Response({'error': 'member_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        member = get_object_or_404(Member, id=member_id)
        
        with transaction.atomic():
            calling, _ = CallingList.objects.get_or_create(program=program, member=member)
            calling.status = 'called'
            calling.save()
            
            # Create marksheets for all assigned judges
            for judge in program.judges.all():
                Marksheet.objects.get_or_create(program=program, judge=judge, member=member)
                
        judge_code = calling.calling_code.split('-')[1] if '-' in calling.calling_code else calling.calling_code
        return Response({
            'status': 'ok',
            'judge_code': judge_code,
            'member_name': member.name,
            'member_chest_no': member.chest_no
        })

class LotRespinAPIView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, program_id):
        program = get_object_or_404(Program, id=program_id)
        
        with transaction.atomic():
            CallingList.objects.filter(program=program).delete()
            Marksheet.objects.filter(program=program).delete()
            Result.objects.filter(program=program).delete()
            
            from results.utils import recalculate_team_points
            recalculate_team_points()
            
        return Response({'message': f'Lot codes reset for all participants in program {program.name}'})

# ────────────────────────────────────────────────────────
#  ADMIN & PUBLIC DASHBOARD STATS APIS
# ────────────────────────────────────────────────────────

class AdminDashboardStatsAPIView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        results_count = Result.objects.count()
        members_count = Member.objects.count()
        marksheets_count = Marksheet.objects.count()
        programs_count = Program.objects.count()
        teams_count = Team.objects.count()
        categories_count = Category.objects.count()
        judges_count = User.objects.filter(userprofile__role='judge').count()
        
        # Calculate active and final programs
        final_programs_ids = Result.objects.values_list('program_id', flat=True).distinct()
        final_programs_count = len(final_programs_ids)
        
        active_programs_count = Program.objects.filter(
            Q(marksheets__isnull=False) | Q(calling_lists__isnull=False)
        ).exclude(id__in=final_programs_ids).distinct().count()

        # Stages count (actual defined stages)
        stages_count = Stage.objects.count()

        # Participants by Team
        participants_by_team = []
        for t in Team.objects.all():
            participants_by_team.append({
                'team_name': t.name,
                'member_count': t.members.count()
            })

        # Participants by Category
        participants_by_category = []
        for c in Category.objects.all():
            participants_by_category.append({
                'category_name': c.name,
                'member_count': c.members.count()
            })

        # Team Leaderboard
        team_leaderboard = []
        for tp in TeamPoints.objects.select_related('team').order_by('-total_points'):
            team_leaderboard.append({
                'team_name': tp.team.name,
                'total_points': tp.total_points
            })

        marksheets_submitted = Marksheet.objects.filter(submitted=True).count()
        marksheets_pending = Marksheet.objects.filter(submitted=False).count()

        return Response({
            'results_count': results_count,
            'members_count': members_count,
            'marksheets_count': marksheets_count,
            'programs_count': programs_count,
            'teams_count': teams_count,
            'categories_count': categories_count,
            'judges_count': judges_count,
            'active_programs_count': active_programs_count,
            'final_programs_count': final_programs_count,
            'stages_count': stages_count,
            'participants_by_team': participants_by_team,
            'participants_by_category': participants_by_category,
            'team_leaderboard': team_leaderboard,
            'marksheets_submitted': marksheets_submitted,
            'marksheets_pending': marksheets_pending
        })

class PublicDashboardStatsAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Fest Settings
        fest = FestSettings.objects.first()
        fest_data = FestSettingsSerializer(fest).data if fest else None
        
        # Categories
        cats = Category.objects.all()
        cats_data = CategorySerializer(cats, many=True).data
        
        # Schedule
        progs = Program.objects.all().order_by('schedule')
        progs_data = ProgramSerializer(progs, many=True).data
        
        # Team points leaderboard
        teampoints = TeamPoints.objects.select_related('team').order_by('-total_points')
        teampoints_data = TeamPointsSerializer(teampoints, many=True).data
        
        # Individual Leaderboard — top 20 per category (only counting program__type='single')
        result_categories = (
            Result.objects.filter(published=True, program__type='single')
            .values('member__category__id', 'member__category__name')
            .distinct()
        )

        individual_data = []
        for cat in result_categories:
            cat_id = cat['member__category__id']
            cat_name = cat['member__category__name']

            # Top 20 for this category
            cat_leaderboard = (
                Result.objects.filter(published=True, member__category__id=cat_id, program__type='single')
                .values('member__id', 'member__name', 'member__team__name')
                .annotate(total=Sum('points'), events=Count('id'))
                .order_by('-total')[:20]
            )

            # Per-program breakdown for this category's top members
            cat_member_ids = [item['member__id'] for item in cat_leaderboard]
            per_prog = (
                Result.objects.filter(published=True, member__id__in=cat_member_ids, program__type='single')
                .values('member__id', 'program__id', 'program__name', 'points', 'rank')
                .order_by('member__id', 'program__name')
            )
            prog_map = {}
            for r in per_prog:
                mid = r['member__id']
                if mid not in prog_map:
                    prog_map[mid] = []
                prog_map[mid].append({
                    'program_id': r['program__id'],
                    'program_name': r['program__name'],
                    'points': r['points'],
                    'rank': r['rank'],
                })

            individual_data.append({
                'category_id': cat_id,
                'category_name': cat_name,
                'performers': [{
                    'member_id': item['member__id'],
                    'member_name': item['member__name'],
                    'team_name': item['member__team__name'],
                    'total_points': item['total'],
                    'events_count': item['events'],
                    'program_breakdown': prog_map.get(item['member__id'], []),
                } for item in cat_leaderboard],
            })

        # Programs with results
        published_program_ids = Result.objects.filter(published=True).values_list('program_id', flat=True).distinct()
        progs_with_results = Program.objects.filter(id__in=published_program_ids).order_by('-schedule')
        progs_with_results_data = [{'id': p.id, 'name': p.name, 'category_name': p.category.name} for p in progs_with_results]

        return Response({
            'fest_settings': fest_data,
            'categories': cats_data,
            'schedule': progs_data,
            'leaderboard': teampoints_data,
            'individual_leaderboard': individual_data,
            'programs_with_results': progs_with_results_data
        })

# ────────────────────────────────────────────────────────
#  REPORTS APIS
# ────────────────────────────────────────────────────────

class AdminReportsAPIView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        report_type = request.query_params.get('type', 'dashboard')
        
        if report_type == 'results':
            program_id = request.query_params.get('program')
            if program_id:
                if ',' in program_id:
                    ids = [pid.strip() for pid in program_id.split(',') if pid.strip()]
                    programs = Program.objects.filter(id__in=ids).order_by('name')
                    multiple_results = []
                    for p in programs:
                        results = Result.objects.filter(program=p).select_related('member', 'member__team').order_by('rank')
                        serializer = ResultSerializer(results, many=True)
                        multiple_results.append({
                            'program_id': p.id,
                            'program_name': p.name,
                            'category_name': p.category.name if p.category else '',
                            'results': serializer.data
                        })
                    return Response({'multiple_results': multiple_results})
                else:
                    results = Result.objects.filter(program_id=program_id).select_related('member', 'member__team').order_by('rank')
                    serializer = ResultSerializer(results, many=True)
                    return Response({'results': serializer.data})

            
            # List of programs and results status
            programs = Program.objects.all().order_by('name')
            data = []
            for p in programs:
                data.append({
                    'id': p.id,
                    'name': p.name,
                    'category_name': p.category.name,
                    'has_results': p.results.exists(),
                    'is_published': p.results.filter(published=True).exists(),
                    'results_count': p.results.count()
                })
            return Response({'programs': data})

        elif report_type == 'members':
            team_id = request.query_params.get('team')
            category_id = request.query_params.get('category')
            members = Member.objects.select_related('team', 'category').all().order_by('team__name', 'chest_no')
            if team_id:
                members = members.filter(team_id=team_id)
            if category_id:
                members = members.filter(category_id=category_id)
            serializer = MemberSerializer(members, many=True)
            return Response({'members': serializer.data})

        elif report_type == 'marksheets':
            program_id = request.query_params.get('program')
            judge_id = request.query_params.get('judge')
            status_filter = request.query_params.get('status')
            
            if not program_id:
                return Response({'error': 'program parameter is required for marksheet reports.'}, status=status.HTTP_400_BAD_REQUEST)
                
            sheets = Marksheet.objects.filter(program_id=program_id).select_related('member', 'member__team', 'judge').order_by('judge__username', 'member__name')
            if judge_id:
                sheets = sheets.filter(judge_id=judge_id)
            if status_filter == 'submitted':
                sheets = sheets.filter(submitted=True)
            elif status_filter == 'draft':
                sheets = sheets.filter(submitted=False)
                
            serializer = MarksheetSerializer(sheets, many=True)
            return Response({'sheets': serializer.data})

        elif report_type == 'teampoints':
            team_points = TeamPoints.objects.select_related('team').order_by('-total_points')
            serializer = TeamPointsSerializer(team_points, many=True)
            return Response({'teampoints': serializer.data})

        elif report_type == 'schedule':
            category_id = request.query_params.get('category')
            venue = request.query_params.get('venue')
            programs = Program.objects.select_related('category').all().order_by('schedule', 'venue', 'name')
            if category_id:
                programs = programs.filter(category_id=category_id)
            if venue:
                programs = programs.filter(venue__icontains=venue)
            
            # Exclude unscheduled events from the printed schedule report
            programs = programs.exclude(schedule=None)
            serializer = ProgramSerializer(programs, many=True)
            
            # Fetch fest settings to retrieve configured dates
            fest = FestSettings.objects.first()
            fest_dates = fest.dates if fest else []

            return Response({
                'schedule': serializer.data,
                'fest_dates': fest_dates
            })

        return Response({'error': 'Invalid report type.'}, status=status.HTTP_400_BAD_REQUEST)

# ────────────────────────────────────────────────────────
#  USER/JUDGE MANAGEMENT APIS
# ────────────────────────────────────────────────────────

class UserManagementViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        role_filter = self.request.query_params.get('role')
        if role_filter:
            return User.objects.filter(userprofile__role=role_filter)
        return User.objects.all()

    @action(detail=False, methods=['post'])
    def add_judge(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        assigned_programs = request.data.get('assigned_programs', []) # list of program IDs

        if not username or not password:
            return Response({'error': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            UserProfile.objects.create(user=user, role='judge')
            
            # Assign programs
            if assigned_programs:
                programs = Program.objects.filter(id__in=assigned_programs)
                for prog in programs:
                    prog.judges.add(user)

        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def edit_user(self, request, pk=None):
        user = self.get_object()
        username = request.data.get('username')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        password = request.data.get('password')
        assigned_programs = request.data.get('assigned_programs') # list of program IDs

        if not username:
            return Response({'error': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exclude(id=user.id).exists():
            return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            if password:
                user.set_password(password)
            user.save()

            # If judge role, update programs
            if hasattr(user, 'userprofile') and user.userprofile.role == 'judge' and assigned_programs is not None:
                user.assigned_programs.clear()
                programs = Program.objects.filter(id__in=assigned_programs)
                for prog in programs:
                    prog.judges.add(user)

        serializer = UserSerializer(user)
        return Response(serializer.data)

# ────────────────────────────────────────────────────────
#  POSTER TEMPLATE & RENDERING
# ────────────────────────────────────────────────────────

class GlobalPosterTemplateViewSet(viewsets.ModelViewSet):
    """CRUD for the single global poster template."""
    queryset = GlobalPosterTemplate.objects.all()
    serializer_class = GlobalPosterTemplateSerializer
    permission_classes = [ReadOnlyOrAdmin]

    def list(self, request):
        # Always return a single object (get or create)
        obj, _ = GlobalPosterTemplate.objects.get_or_create(pk=1)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    def create(self, request):
        obj, _ = GlobalPosterTemplate.objects.get_or_create(pk=1)
        image = request.FILES.get('image_file')
        config = request.data.get('config')

        if image:
            obj.image_file = image
        if config:
            if isinstance(config, str):
                obj.config = json.loads(config)
            else:
                obj.config = config
        obj.save()
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        obj, _ = GlobalPosterTemplate.objects.get_or_create(pk=1)
        image = request.FILES.get('image_file')
        config = request.data.get('config')

        if image:
            obj.image_file = image
        if config:
            if isinstance(config, str):
                obj.config = json.loads(config)
            else:
                obj.config = config
        obj.save()
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PosterRenderAPIView(APIView):
    """Render a poster PNG for a given program's published results."""
    permission_classes = [permissions.AllowAny]

    POSTER_W = 2480
    POSTER_H = 3100

    def get(self, request, program_id):
        from PIL import Image, ImageDraw, ImageFont
        import io
        from django.conf import settings
        import os

        program = get_object_or_404(Program, id=program_id)
        results = Result.objects.filter(
            program=program, published=True
        ).order_by('rank')[:3]

        if not results.exists():
            return Response(
                {'error': 'No published results for this program.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Load template config
        template = GlobalPosterTemplate.objects.first()
        config = template.config if template else {}
        if not config:
            from programs.models import default_poster_config
            config = default_poster_config()

        template_path = template.image_file.path if template and template.image_file else None

        from results.utils import generate_winner_poster
        bg = generate_winner_poster(template_path, program, results, config=config)

        # Convert to PNG bytes
        import io
        output = io.BytesIO()
        bg.convert('RGB').save(output, format='PNG', quality=95)
        output.seek(0)

        download = request.query_params.get('download')
        from django.http import HttpResponse
        response = HttpResponse(output.read(), content_type='image/png')

        if download:
            safe_name = program.name.replace(' ', '_').replace('/', '-')
            response['Content-Disposition'] = f'attachment; filename="poster_{safe_name}.png"'

        return response
