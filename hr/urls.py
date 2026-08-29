"""Маршруты модуля «Кадровый учёт» (2.5)."""
from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    # Дашборд кадров
    path('', views.HrDashboardView.as_view(), name='dashboard'),

    # Сотрудники (форма Т-2)
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/new/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee_detail'),
    path('employees/<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee_update'),
    path('employees/<int:pk>/card/', views.EmployeeCardView.as_view(), name='employee_card'),

    # Штатное расписание
    path('staffing/', views.StaffingView.as_view(), name='staffing'),
    path('staffing/new/', views.StaffPositionCreateView.as_view(), name='position_create'),

    # Тарификация
    path('tarification/', views.TarificationListView.as_view(), name='tarification_list'),
    path('tarification/new/', views.TarificationCreateView.as_view(), name='tarification_create'),
    path('tarification/<int:pk>/', views.TarificationDetailView.as_view(), name='tarification_detail'),
    path('tarification/<int:period_pk>/items/new/', views.TarificationItemCreateView.as_view(),
         name='tarification_item_create'),

    # Выгрузка в 1С:Зарплата
    path('salary/', views.SalaryExportListView.as_view(), name='salary_list'),
    path('salary/new/', views.SalaryExportCreateView.as_view(), name='salary_create'),
    path('salary/<int:pk>/download/', views.SalaryExportDownloadView.as_view(), name='salary_download'),

    # Приказы по личному составу
    path('orders/', views.HROrderListView.as_view(), name='order_list'),
    path('orders/new/', views.HROrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.HROrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/print/', views.HROrderPrintView.as_view(), name='order_print'),
]
