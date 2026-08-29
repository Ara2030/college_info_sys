"""Админ-панель модуля «Контингент студентов» (2.1)."""
from django.contrib import admin

from .models import (Department, Specialty, Group, Student, StudentDocument,
                     ParentInfo, OrderType, Order, OrderItem,
                     StudentStatusHistory, AcademicLeave, RegistryExport)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 2


class StudentDocumentInline(admin.TabularInline):
    model = StudentDocument
    extra = 1


class ParentInfoInline(admin.TabularInline):
    model = ParentInfo
    extra = 1


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'group', 'specialty', 'status', 'enroll_date')
    list_filter = ('status', 'group__department', 'group')
    search_fields = ('last_name', 'first_name', 'middle_name', 'snils', 'student_card_number')
    inlines = (StudentDocumentInline, ParentInfoInline)
    list_select_related = ('group', 'specialty')
    autocomplete_fields = ('group',)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialty', 'department', 'course', 'enroll_year')
    list_filter = ('department', 'course')
    search_fields = ('name',)
    autocomplete_fields = ('specialty',)


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'qualification', 'department', 'duration_months')
    list_filter = ('department',)
    search_fields = ('code', 'name')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('number', 'date', 'order_type', 'title', 'status')
    list_filter = ('order_type', 'status')
    search_fields = ('number', 'title')
    inlines = (OrderItemInline,)
    date_hierarchy = 'date'


@admin.register(OrderType)
class OrderTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')


@admin.register(StudentStatusHistory)
class StudentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'status_from', 'status_to', 'order')
    list_filter = ('status_to',)
    search_fields = ('student__last_name', 'student__first_name')


@admin.register(RegistryExport)
class RegistryExportAdmin(admin.ModelAdmin):
    list_display = ('period_start', 'created_at', 'status', 'student_count', 'order_count')


admin.site.register(Department)
admin.site.register(AcademicLeave)
