from rest_framework import serializers
from .models import Result, TeamPoints

class ResultSerializer(serializers.ModelSerializer):
    program_name = serializers.ReadOnlyField(source='program.name')
    category_name = serializers.ReadOnlyField(source='program.category.name')
    member_name = serializers.ReadOnlyField(source='member.name')
    member_chest_no = serializers.ReadOnlyField(source='member.chest_no')
    team_name = serializers.ReadOnlyField(source='member.team.name')

    class Meta:
        model = Result
        fields = [
            'id', 'program', 'program_name', 'category_name', 'member', 
            'member_name', 'member_chest_no', 'team_name', 'total_marks', 
            'rank', 'points', 'judge_code', 'published', 'grade'
        ]

class TeamPointsSerializer(serializers.ModelSerializer):
    team_name = serializers.ReadOnlyField(source='team.name')

    class Meta:
        model = TeamPoints
        fields = ['id', 'team', 'team_name', 'total_points', 'breakdown']
