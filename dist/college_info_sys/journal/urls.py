"""Маршруты модуля «Электронный журнал» (2.2)."""
from django.urls import path
from . import views

app_name = 'journal'

urlpatterns = [
    # Журналы занятий
    path('', views.JournalGroupListView.as_view(), name='group_list'),
    path('groups/<int:pk>/', views.JournalGroupView.as_view(), name='group_detail'),

    # Занятия
    path('lessons/new/', views.LessonCreateView.as_view(), name='lesson_create'),
    path('lessons/<int:pk>/', views.LessonDetailView.as_view(), name='lesson_detail'),
    path('lessons/<int:pk>/edit/', views.LessonUpdateView.as_view(), name='lesson_update'),

    # Отчёты
    path('reports/groups/<int:pk>/', views.GroupReportView.as_view(), name='group_report'),
    path('reports/students/<int:pk>/', views.StudentProgressView.as_view(), name='student_progress'),

    # Уведомления о низкой успеваемости
    path('low-performance/', views.LowPerformanceView.as_view(), name='low_performance'),
]
