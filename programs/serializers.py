from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import FestSettings, Category, Program, PosterTemplate, GlobalPosterTemplate, ProgramGradeSetting, Stage, ActivityLog

class FestSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FestSettings
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    programs_count = serializers.IntegerField(source='programs.count', read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'chest_prefix', 'programs_count', 'fest']

class ProgramGradeSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgramGradeSetting
        fields = '__all__'

class UserBriefSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

class ProgramSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    judges_details = UserBriefSerializer(source='judges', many=True, read_only=True)
    registered_members_count = serializers.SerializerMethodField(read_only=True)
    calculated_duration_minutes = serializers.ReadOnlyField()
    end_time = serializers.ReadOnlyField()
    has_results = serializers.SerializerMethodField(read_only=True)
    is_published = serializers.SerializerMethodField(read_only=True)
    lot_completed = serializers.SerializerMethodField(read_only=True)
    has_marksheets = serializers.SerializerMethodField(read_only=True)
    lot_spun_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Program
        fields = [
            'id', 'name', 'category', 'category_name', 'type', 'group_size', 'stage_type',
            'duration', 'calculated_duration_minutes', 'end_time', 'participant_limit',
            'point_weightage_1st', 'point_weightage_2nd', 'point_weightage_3rd', 'max_marks', 
            'schedule', 'venue', 'judges', 'judges_details', 'registered_members_count',
            'has_results', 'is_published', 'lot_completed', 'has_marksheets', 'lot_spun_at', 'fest'
        ]
        extra_kwargs = {
            'judges': {'required': False}
        }

    def validate(self, attrs):
        duration = attrs.get('duration', self.instance.duration if self.instance else 5)
        stage_type = attrs.get('stage_type', self.instance.stage_type if self.instance else 'onstage')
        venue = attrs.get('venue', self.instance.venue if self.instance else '')
        schedule = attrs.get('schedule', self.instance.schedule if self.instance else None)

        if schedule and venue:
            registered_count = self.instance.registered_members.count() if self.instance else 0
            count_mult = max(1, registered_count)
            total_duration = max(5, duration if stage_type == 'offstage' else duration * count_mult)
            start_time = schedule
            import datetime
            end_time = start_time + datetime.timedelta(minutes=total_duration)

            # Check overlap against other programs at the same venue
            clashing_programs = Program.objects.filter(venue=venue).exclude(schedule=None)
            if self.instance:
                clashing_programs = clashing_programs.exclude(id=self.instance.id)

            for other in clashing_programs:
                other_start = other.schedule
                other_dur = other.calculated_duration_minutes
                other_end = other_start + datetime.timedelta(minutes=other_dur)

                # Overlap condition: start_time < other_end and other_start < end_time
                if start_time < other_end and other_start < end_time:
                    other_start_str = other_start.strftime('%I:%M %p')
                    other_end_str = other_end.strftime('%I:%M %p')
                    raise serializers.ValidationError(
                        f"Time Clash: The event '{other.name}' is already scheduled at venue '{venue}' "
                        f"from {other_start_str} to {other_end_str}."
                    )

        return attrs

    def get_registered_members_count(self, obj):
        if '_prefetched_objects_cache' in obj.__dict__ and 'registered_members' in obj._prefetched_objects_cache:
            return len(obj.registered_members.all())
        return obj.registered_members.count()

    def get_has_results(self, obj):
        if '_prefetched_objects_cache' in obj.__dict__ and 'results' in obj._prefetched_objects_cache:
            return len(obj.results.all()) > 0
        return obj.results.exists()

    def get_is_published(self, obj):
        if '_prefetched_objects_cache' in obj.__dict__ and 'results' in obj._prefetched_objects_cache:
            return any(r.published for r in obj.results.all())
        return obj.results.filter(published=True).exists()

    def get_has_marksheets(self, obj):
        if '_prefetched_objects_cache' in obj.__dict__ and 'marksheets' in obj._prefetched_objects_cache:
            return len(obj.marksheets.all()) > 0
        return obj.marksheets.exists()

    def get_lot_completed(self, obj):
        if '_prefetched_objects_cache' in obj.__dict__ and 'registered_members' in obj._prefetched_objects_cache:
            reg_count = len(obj.registered_members.all())
        else:
            reg_count = obj.registered_members.count()

        if reg_count == 0:
            return False

        if '_prefetched_objects_cache' in obj.__dict__ and 'calling_lists' in obj._prefetched_objects_cache:
            called_count = sum(1 for c in obj.calling_lists.all() if c.status == 'called')
        else:
            called_count = obj.calling_lists.filter(status='called').count()

        return called_count >= reg_count

    def get_lot_spun_at(self, obj):
        if '_prefetched_objects_cache' in obj.__dict__ and 'calling_lists' in obj._prefetched_objects_cache:
            called_lists = [c for c in obj.calling_lists.all() if c.status == 'called']
            if not called_lists:
                return None
            times = [c.called_at or c.created_at for c in called_lists if c.called_at or c.created_at]
            if not times:
                return None
            earliest = min(times)
            return earliest.isoformat() if earliest else None
        else:
            called = obj.calling_lists.filter(status='called').order_by('called_at', 'created_at').first()
            if called:
                val = called.called_at or called.created_at
                return val.isoformat() if val else None
        return None

class PosterTemplateSerializer(serializers.ModelSerializer):
    program_name = serializers.ReadOnlyField(source='program.name')

    class Meta:
        model = PosterTemplate
        fields = ['id', 'program', 'program_name', 'image_file', 'config', 'uploaded_at']

class GlobalPosterTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalPosterTemplate
        fields = ['id', 'image_file', 'config']

class StageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = '__all__'

class ActivityLogSerializer(serializers.ModelSerializer):
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'fest', 'user', 'user_name', 'action_type',
            'title', 'description', 'target_model', 'target_id',
            'metadata', 'created_at', 'time_ago'
        ]

    def get_time_ago(self, obj):
        if not obj.created_at:
            return ""
        diff = timezone.now() - obj.created_at
        seconds = int(diff.total_seconds())
        if seconds < 10:
            return "Just now"
        elif seconds < 60:
            return f"{seconds}s ago"
        elif seconds < 3600:
            return f"{seconds // 60}m ago"
        elif seconds < 86400:
            return f"{seconds // 3600}h ago"
        elif seconds < 604800:
            return f"{seconds // 86400}d ago"
        else:
            return obj.created_at.strftime("%b %d, %Y")

