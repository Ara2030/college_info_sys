"""Маршруты модуля «Авторизация и роли»."""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.AppLoginView.as_view(), name='login'),
    path('login/clear-demo/', views.ClearDemoDataView.as_view(), name='clear_demo_data'),
    path('logout/', views.AppLogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),

    # Управление пользователями (администратор)
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/new/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),

    # Безопасность
    path('security/', views.SecurityLogView.as_view(), name='security_log'),
]
