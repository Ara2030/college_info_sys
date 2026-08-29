"""Маршруты модуля «Контингент студентов» (2.1)."""
from django.urls import path
from . import views, views_registry

app_name = 'contingent'

urlpatterns = [
    # Дашборд (главная)
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Студенты
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('students/new/', views.StudentCreateView.as_view(), name='student_create'),
    path('students/<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('students/<int:pk>/edit/', views.StudentUpdateView.as_view(), name='student_update'),
    path('students/<int:pk>/delete/', views.StudentDeleteView.as_view(), name='student_delete'),

    # Группы
    path('groups/', views.GroupListView.as_view(), name='group_list'),
    path('groups/new/', views.GroupCreateView.as_view(), name='group_create'),
    path('groups/<int:pk>/', views.GroupDetailView.as_view(), name='group_detail'),
    path('groups/<int:pk>/edit/', views.GroupUpdateView.as_view(), name='group_update'),
    path('groups/<int:pk>/delete/', views.GroupDeleteView.as_view(), name='group_delete'),

    # Приказы
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/new/', views.OrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/post/', views.OrderPostView.as_view(), name='order_post'),

    # Выгрузка в Реестр СПО
    path('exports/', views_registry.export_registry_list, name='export_list'),
    path('exports/<int:pk>/', views_registry.export_registry_detail, name='export_detail'),
    path('exports/<int:pk>/download/', views_registry.export_registry_download, name='export_download'),
]
