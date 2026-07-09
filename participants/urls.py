from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.teamlead_dashboard, name='teamlead_dashboard'),
    path('add-member/', views.add_member, name='add_member'),
    path('member/<int:member_id>/assign/', views.assign_program, name='assign_program'),
]
