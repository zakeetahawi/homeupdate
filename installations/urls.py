from django.urls import path, include
from . import views

app_name = 'installations'

urlpatterns = [
    # النظام القديم - للتوافق
    path('legacy/', include([
        # Dashboard
        path('', views.InstallationDashboardView.as_view(), name='legacy_dashboard'),

        # Installation URLs
        path('list/', views.InstallationListView.as_view(), name='legacy_installation_list'),
        path('create/', views.InstallationCreateView.as_view(), name='legacy_installation_create'),
        path('<int:pk>/', views.InstallationDetailView.as_view(), name='legacy_installation_detail'),
        path('<int:pk>/update/', views.InstallationUpdateView.as_view(), name='legacy_installation_update'),
        path('<int:pk>/delete/', views.InstallationDeleteView.as_view(), name='legacy_installation_delete'),

        # Installation Steps API
        path('api/installation/<int:installation_id>/steps/add/', views.add_installation_step, name='legacy_add_installation_step'),
        path('api/steps/<int:step_id>/complete/', views.mark_step_complete, name='legacy_mark_step_complete'),

        # Quality Checks API
        path('api/installation/<int:installation_id>/quality-checks/add/', views.add_quality_check, name='legacy_add_quality_check'),
    ])),

    # النظام الجديد المتقدم
    path('', include('installations.urls_new')),
]
