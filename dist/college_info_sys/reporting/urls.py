"""Маршруты модуля «Отчётность и интеграция» (2.6)."""
from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # Дашборд
    path('', views.ReportingDashboardView.as_view(), name='dashboard'),

    # Статистические отчёты (СПО-1, СПО-2, мониторинг)
    path('stat/', views.StatReportListView.as_view(), name='stat_list'),
    path('stat/new/', views.StatReportCreateView.as_view(), name='stat_create'),
    path('stat/<int:pk>/', views.StatReportDetailView.as_view(), name='stat_detail'),
    path('stat/<int:pk>/excel/', views.StatReportExcelView.as_view(), name='stat_excel'),
    path('stat/<int:pk>/pdf/', views.StatReportPdfView.as_view(), name='stat_pdf'),

    # REST API Реестра студентов СПО (XML)
    path('registry/', views.RegistryApiView.as_view(), name='registry_api'),

    # СМЭВ
    path('smev/', views.SmevView.as_view(), name='smev'),

    # Журнал интеграций
    path('logs/', views.IntegrationLogListView.as_view(), name='logs'),
]
