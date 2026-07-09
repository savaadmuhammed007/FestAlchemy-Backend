from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('results/<int:program_id>/', views.program_results, name='program_results'),
]
