from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    LoginAPIView, LogoutAPIView, MeAPIView,
    FestSettingsViewSet, CategoryViewSet, ProgramGradeSettingViewSet,
    ProgramViewSet, TeamViewSet, MemberViewSet, MarksheetViewSet,
    ResultViewSet, TeamPointsViewSet, UserManagementViewSet, StageViewSet,
    LotCallingAPIView, LotRespinAPIView,
    AdminDashboardStatsAPIView, PublicDashboardStatsAPIView,
    AdminReportsAPIView,
    GlobalPosterTemplateViewSet, PosterRenderAPIView
)

router = DefaultRouter()
router.register(r'fest-settings', FestSettingsViewSet, basename='fest-settings')
router.register(r'stages', StageViewSet, basename='stages')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'grade-settings', ProgramGradeSettingViewSet, basename='grade-settings')
router.register(r'programs', ProgramViewSet, basename='programs')
router.register(r'teams', TeamViewSet, basename='teams')
router.register(r'members', MemberViewSet, basename='members')
router.register(r'marksheets', MarksheetViewSet, basename='marksheets')
router.register(r'results', ResultViewSet, basename='results')
router.register(r'teampoints', TeamPointsViewSet, basename='teampoints')
router.register(r'users', UserManagementViewSet, basename='users')
router.register(r'poster-template', GlobalPosterTemplateViewSet, basename='poster-template')

urlpatterns = [
    # Auth Endpoints
    path('auth/login/', LoginAPIView.as_view(), name='api-login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api-logout'),
    path('auth/me/', MeAPIView.as_view(), name='api-me'),

    # Lot Spinning & Calling
    path('calling/<int:program_id>/', LotCallingAPIView.as_view(), name='api-calling'),
    path('calling/<int:program_id>/respin/', LotRespinAPIView.as_view(), name='api-calling-respin'),

    # Dashboards & Reports
    path('admin/stats/', AdminDashboardStatsAPIView.as_view(), name='api-admin-stats'),
    path('public/stats/', PublicDashboardStatsAPIView.as_view(), name='api-public-stats'),
    path('reports/', AdminReportsAPIView.as_view(), name='api-reports'),

    # Poster Rendering
    path('v1/results/poster/<int:program_id>/', PosterRenderAPIView.as_view(), name='api-poster-render'),

    # Router Endpoints
    path('v1/', include(router.urls)),
]
