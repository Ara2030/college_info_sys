"""Маршруты модуля «Промежуточная аттестация» (2.3)."""
from django.urls import path
from . import views

app_name = 'attestation'

urlpatterns = [
    # Расписание экзаменов и зачётов
    path('', views.ExamListView.as_view(), name='exam_list'),
    path('new/', views.ExamCreateView.as_view(), name='exam_create'),
    path('<int:pk>/', views.ExamDetailView.as_view(), name='exam_detail'),
    path('<int:pk>/edit/', views.ExamUpdateView.as_view(), name='exam_update'),
    path('<int:pk>/print/', views.ExamPrintView.as_view(), name='exam_print'),
    path('schedule/build/', views.ScheduleBuildView.as_view(), name='schedule_build'),

    # Академические задолженности
    path('debts/', views.DebtListView.as_view(), name='debt_list'),
    path('debts/order/generate/', views.DebtGenerateOrderView.as_view(), name='debt_order_generate'),
    path('debts/<int:pk>/clear/', views.DebtClearView.as_view(), name='debt_clear'),

    # Стипендия
    path('scholarship/', views.ScholarshipListView.as_view(), name='scholarship_list'),
    path('scholarship/new/', views.ScholarshipCreateView.as_view(), name='scholarship_create'),
    path('scholarship/<int:pk>/', views.ScholarshipDetailView.as_view(), name='scholarship_detail'),
]
