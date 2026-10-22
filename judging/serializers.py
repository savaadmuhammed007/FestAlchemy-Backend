from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Marksheet
from participants.serializers import MemberSerializer
from participants.models import CallingList

class MarksheetSerializer(serializers.ModelSerializer):
    program_name = serializers.ReadOnlyField(source='program.name')
    member_name = serializers.ReadOnlyField(source='member.name')
    member_chest_no = serializers.ReadOnlyField(source='member.chest_no')
    member_team_name = serializers.ReadOnlyField(source='member.team.name')
    judge_username = serializers.ReadOnlyField(source='judge.username')
    judge_code = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

    class Meta:
        model = Marksheet
        fields = [
            'id', 'program', 'program_name', 'member', 'member_name', 
            'member_chest_no', 'member_team_name', 'judge', 'judge_username', 
            'judge_code', 'marks', 'score', 'submitted'
        ]
        read_only_fields = ['judge_code', 'marks']

    def get_judge_code(self, obj):
        # Use batch context map if available to eliminate N+1 queries
        calling_map = self.context.get('calling_map') if self.context else None
        if calling_map is not None:
            raw_code = calling_map.get((obj.program_id, obj.member_id))
        else:
            calling = CallingList.objects.filter(program_id=obj.program_id, member_id=obj.member_id).first()
            raw_code = calling.calling_code if calling else None

        if raw_code and '-' in raw_code:
            return raw_code.split('-')[1]
        return raw_code or "N/A"

    def get_score(self, obj):
        raw = obj.marks
        if isinstance(raw, dict):
            total = raw.get('total')
            if total is None:
                try:
                    total = sum(float(v) for v in raw.values() if str(v).replace('.', '', 1).isdigit())
                except Exception:
                    total = 0.0
            return total
        else:
            try:
                return float(raw) if raw else 0.0
            except (TypeError, ValueError):
                return 0.0

    def validate(self, attrs):
        # We need to extract score from initial data if it's there
        score = self.initial_data.get('score')
        if score is not None:
            try:
                score_val = float(score)
            except (ValueError, TypeError):
                raise serializers.ValidationError({"score": "Score must be a number."})
            
            # Check maximum marks
            program = attrs.get('program', self.instance.program if self.instance else None)
            if program and score_val > program.max_marks:
                raise serializers.ValidationError({"score": f"Marks cannot exceed maximum allowed marks ({program.max_marks})."})
            if score_val < 0:
                raise serializers.ValidationError({"score": "Marks cannot be negative."})
            
        return attrs

    def update(self, instance, validated_data):
        score = self.initial_data.get('score')
        if score is not None:
            instance.marks = {'total': float(score)}
        
        # If 'submitted' is in initial_data, we can update it
        if 'submitted' in self.initial_data:
            instance.submitted = bool(self.initial_data['submitted'])

        return super().update(instance, validated_data)
