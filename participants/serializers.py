from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Team, Member, CallingList
from programs.serializers import CategorySerializer, ProgramSerializer

class TeamSerializer(serializers.ModelSerializer):
    teamlead_username = serializers.ReadOnlyField(source='teamlead.username')
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'teamlead', 'teamlead_username', 'members_count']

    def get_members_count(self, obj):
        if hasattr(obj, 'members_count'):
            return obj.members_count
        return obj.members.count()

class MemberSerializer(serializers.ModelSerializer):
    team_name = serializers.ReadOnlyField(source='team.name')
    category_name = serializers.ReadOnlyField(source='category.name')
    chest_number = serializers.ReadOnlyField(source='chest_no')
    registered_programs_details = serializers.SerializerMethodField(read_only=True)
    programs = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Member
        fields = [
            'id', 'name', 'team', 'team_name', 'category', 'category_name',
            'chest_no', 'chest_number', 'registered_programs', 'registered_programs_details', 'programs'
        ]
        read_only_fields = ['chest_no', 'chest_number']
        extra_kwargs = {
            'team': {'required': False, 'allow_null': True},
            'registered_programs': {'required': False}
        }

    def get_registered_programs_details(self, obj):
        return [{'id': p.id, 'name': p.name, 'type': p.type, 'stage_type': p.stage_type} for p in obj.registered_programs.all()]

    def get_programs(self, obj):
        return [{'id': p.id, 'name': p.name, 'type': p.type, 'stage_type': p.stage_type} for p in obj.registered_programs.all()]

class CallingListSerializer(serializers.ModelSerializer):
    program_name = serializers.ReadOnlyField(source='program.name')
    member_name = serializers.ReadOnlyField(source='member.name')
    member_chest_no = serializers.ReadOnlyField(source='member.chest_no')
    member_team_name = serializers.ReadOnlyField(source='member.team.name')
    judge_code = serializers.SerializerMethodField()

    class Meta:
        model = CallingList
        fields = [
            'id', 'program', 'program_name', 'member', 'member_name', 
            'member_chest_no', 'member_team_name', 'calling_code', 'judge_code', 'status'
        ]

    def get_judge_code(self, obj):
        if obj.calling_code and '-' in obj.calling_code:
            return obj.calling_code.split('-')[1]
        return obj.calling_code or "N/A"
