"""Маршруты модуля «Формирование расписания» (2.4)."""
from django.urls import path
from . import views

app_name = 'schedule'

urlpatterns = [
    # Портал расписания
    path('', views.SchedulePortalView.as_view(), name='group_list'),
    path('groups/<int:pk>/', views.GroupScheduleView.as_view(), name='group_schedule'),
    path('teachers/', views.TeacherListView.as_view(), name='teacher_list'),
    path('teachers/new/', views.TeacherCreateView.as_view(), name='teacher_create'),
    path('teachers/<int:pk>/', views.TeacherScheduleView.as_view(), name='teacher_schedule'),
    path('teachers/<int:pk>/edit/', views.TeacherUpdateView.as_view(), name='teacher_update'),
    path('teachers/<int:pk>/delete/', views.TeacherDeleteView.as_view(), name='teacher_delete'),

    # Занятия
    path('entries/new/', views.EntryCreateView.as_view(), name='entry_create'),
    path('entries/<int:pk>/replace/', views.EntryReplaceView.as_view(), name='entry_replace'),
    path('entries/<int:pk>/publish/', views.EntryPublishView.as_view(), name='entry_publish'),

    # Автопостроение и контроль конфликтов
    path('build/', views.ScheduleBuildView.as_view(), name='build'),
    path('conflicts/', views.ConflictsView.as_view(), name='conflicts'),
]
