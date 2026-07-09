from rest_framework import serializers
from django.contrib.auth.models import User
from .models import FestSettings, Category, Program, PosterTemplate, GlobalPosterTemplate, ProgramGradeSetting, Stage

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
    registered_members_count = serializers.IntegerField(source='registered_members.count', read_only=True)
    calculated_duration_minutes = serializers.ReadOnlyField()
    end_time = serializers.ReadOnlyField()
    has_results = serializers.SerializerMethodField(read_only=True)
    is_published = serializers.SerializerMethodField(read_only=True)
    lot_completed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Program
        fields = [
            'id', 'name', 'category', 'category_name', 'type', 'group_size', 'stage_type',
            'duration', 'calculated_duration_minutes', 'end_time', 'participant_limit',
            'point_weightage_1st', 'point_weightage_2nd', 'point_weightage_3rd', 'max_marks', 
            'schedule', 'venue', 'judges', 'judges_details', 'registered_members_count',
            'has_results', 'is_published', 'lot_completed', 'fest'
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
            total_duration = duration if stage_type == 'offstage' else duration * registered_count
            start_time = schedule
            import datetime
            end_time = start_time + datetime.timedelta(minutes=total_duration)

            # Check overlap against other programs at the same venue
            clashing_programs = Program.objects.filter(venue=venue).exclude(schedule=None)
            if self.instance:
                clashing_programs = clashing_programs.exclude(id=self.instance.id)

            for other in clashing_programs:
                other_start = other.schedule
                other_count = other.registered_members.count()
                other_dur = other.duration if other.stage_type == 'offstage' else other.duration * other_count
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

    def get_has_results(self, obj):
        return obj.results.exists()

    def get_is_published(self, obj):
        return obj.results.filter(published=True).exists()

    def get_lot_completed(self, obj):
        reg_count = obj.registered_members.count()
        if reg_count == 0:
            return False
        called_count = obj.calling_lists.filter(status='called').count()
        return called_count >= reg_count

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
