from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.admin_dashboard, name='admin_dashboard'),

    # Fest Settings
    path('settings/', views.fest_settings, name='fest_settings'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Programs
    path('programs/', views.program_list, name='program_list'),
    path('programs/add/', views.program_add, name='program_add'),
    path('programs/<int:pk>/edit/', views.program_edit, name='program_edit'),
    path('programs/<int:pk>/delete/', views.program_delete, name='program_delete'),
    path('judge-assignment/', views.judge_assignment_list, name='judge_assignment_list'),
    path('judge-assignment/<int:program_id>/edit/', views.judge_assignment_edit, name='judge_assignment_edit'),
    path('schedule/', views.schedule_list, name='schedule_list'),
    path('schedule/<int:pk>/update/', views.schedule_update, name='schedule_update'),

    # Teams
    path('teams/', views.team_list, name='team_list'),
    path('teams/add/', views.team_add, name='team_add'),
    path('teams/<int:pk>/edit/', views.team_edit, name='team_edit'),
    path('teams/<int:pk>/delete/', views.team_delete, name='team_delete'),

    # Members (admin read/delete only – teamlead adds)
    path('members/', views.member_list, name='member_list'),
    path('members/<int:pk>/delete/', views.member_delete, name='member_delete'),

    # Marksheets (admin read-only overview)
    path('marksheets/', views.marksheet_list, name='marksheet_list'),
    path('marksheets/program/<int:program_id>/', views.marksheet_program_detail, name='marksheet_program_detail'),

    # Results
    path('results/', views.result_list, name='result_list'),
    path('results/program/<int:program_id>/', views.result_program_detail, name='result_program_detail'),
    path('results/add/', views.result_add, name='result_add'),
    path('results/<int:pk>/edit/', views.result_edit, name='result_edit'),
    path('results/<int:pk>/delete/', views.result_delete, name='result_delete'),
    path('results/program/<int:program_id>/publish/', views.toggle_publish_program, name='toggle_publish_program'),
    path('results/compute/<int:program_id>/', views.compute_results, name='compute_results'),
    path('results/poster/<int:program_id>/', views.generate_poster, name='generate_poster'),
    path('results/poster/settings/', views.global_poster_settings, name='global_poster_settings'),
    path('results/poster/<int:program_id>/settings/', views.poster_settings, name='poster_settings'),

    # Code & Grade
    path('spin-lot/', views.spin_lot_list, name='spin_lot_list'),
    path('grade-settings/', views.grade_settings_list, name='grade_settings_list'),
    path('grade-settings/<int:program_id>/edit/', views.grade_setting_edit, name='grade_setting_edit'),

    # Calling UI
    path('calling/<int:program_id>/', views.call_participant, name='call_participant'),
    path('calling/<int:program_id>/respin/', views.respin_program, name='respin_program'),

    # User Management (Judges and Team Leads)
    path('users/judge/add/', views.judge_add, name='judge_add'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),

    # Reports
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/results/', views.report_results, name='report_results'),
    path('reports/members/', views.report_members, name='report_members'),
    path('reports/marksheets/', views.report_marksheets, name='report_marksheets'),
    path('reports/schedule/', views.report_schedule, name='report_schedule'),
    path('reports/teampoints/', views.report_teampoints, name='report_teampoints'),
]

