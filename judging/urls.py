from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.judge_dashboard, name='judge_dashboard'),
    path('evaluate/<int:spreadsheet_id>/', views.evaluate, name='evaluate'),
    path('program/<int:program_id>/list/', views.evaluate_list, name='evaluate_list'),
]
