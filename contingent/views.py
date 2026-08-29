"""Представления (views) модуля «Контингент студентов» (2.1)."""
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (ListView, DetailView, CreateView,
                                  UpdateView, DeleteView, TemplateView)

from .forms import StudentForm, GroupForm, OrderForm, OrderItemFormSet
from .models import (Student, Group, Order, OrderItem, StudentStatus,
                     Department, Specialty, RegistryExport)
from .services.orders import post_order


# ---------------- Дашборд ----------------

class DashboardView(TemplateView):
    """Главная страница: сводная статистика по контингенту."""

    template_name = 'contingent/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        students = Student.objects.all()
        by_status = {s['status']: s['count']
                     for s in students.values('status').annotate(count=Count('id'))}

        ctx['total_students'] = students.count()
        ctx['students_by_status'] = by_status
        ctx['total_groups'] = Group.objects.filter(is_active=True).count()
        ctx['total_departments'] = Department.objects.count()
        ctx['total_specialties'] = Specialty.objects.count()

        orders = Order.objects.all()
        ctx['total_orders'] = orders.count()
        ctx['draft_orders'] = orders.filter(status=Order.Status.DRAFT).count()
        ctx['posted_orders'] = orders.filter(status=Order.Status.POSTED).count()

        ctx['total_exports'] = RegistryExport.objects.count()
        ctx['ready_exports'] = RegistryExport.objects.filter(
            status=RegistryExport.Status.READY).count()

        # Студенты по группам (топ-6 по наполнению)
        ctx['groups_top'] = (Group.objects.select_related('specialty', 'department')
                                          .annotate(count=Count('students'))
                                          .order_by('-count')[:6])
        return ctx


# ---------------- Студенты ----------------

class StudentListView(ListView):
    """Список студентов с поиском и фильтрами (группа, статус)."""
    model = Student
    template_name = 'contingent/student_list.html'
    context_object_name = 'students'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('group', 'specialty', 'group__department')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(last_name__icontains=q) | Q(first_name__icontains=q) |
                Q(middle_name__icontains=q) | Q(student_card_number__icontains=q) |
                Q(snils__icontains=q)
            )
        group_id = self.request.GET.get('group')
        if group_id:
            qs = qs.filter(group_id=group_id)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['groups'] = Group.objects.all()
        ctx['statuses'] = StudentStatus.choices
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_group'] = self.request.GET.get('group', '')
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['total'] = self.get_queryset().count()
        return ctx


class StudentCreateView(CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'contingent/student_form.html'
    success_url = reverse_lazy('contingent:student_list')

    def form_valid(self, form):
        messages.success(self.request, 'Студент добавлен в базу.')
        return super().form_valid(form)


class StudentUpdateView(UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'contingent/student_form.html'
    success_url = reverse_lazy('contingent:student_list')

    def form_valid(self, form):
        messages.success(self.request, 'Данные студента обновлены.')
        return super().form_valid(form)


class StudentDetailView(DetailView):
    """Карточка студента: сведения, документы, родители, история движения."""
    model = Student
    template_name = 'contingent/student_detail.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['documents'] = self.object.documents.all()
        ctx['parents'] = self.object.parents.all()
        ctx['history'] = self.object.status_history.select_related('order').order_by('-date')[:20]
        ctx['leaves'] = self.object.academic_leaves.select_related('order')
        return ctx


class StudentDeleteView(DeleteView):
    model = Student
    template_name = 'contingent/student_confirm_delete.html'
    success_url = reverse_lazy('contingent:student_list')

    def form_valid(self, form):
        messages.success(self.request, 'Карточка студента удалена.')
        return super().form_valid(form)


# ---------------- Группы ----------------

class GroupListView(ListView):
    model = Group
    template_name = 'contingent/group_list.html'
    context_object_name = 'groups'
    paginate_by = 24

    def get_queryset(self):
        return (Group.objects.select_related('specialty', 'department')
                             .annotate(students_count=Count(
                                 'students',
                                 filter=Q(students__status=StudentStatus.STUDY)
                             ))
                             .order_by('name'))


class GroupCreateView(CreateView):
    model = Group
    form_class = GroupForm
    template_name = 'contingent/group_form.html'
    success_url = reverse_lazy('contingent:group_list')


class GroupUpdateView(UpdateView):
    model = Group
    form_class = GroupForm
    template_name = 'contingent/group_form.html'
    success_url = reverse_lazy('contingent:group_list')


class GroupDetailView(DetailView):
    """Группа + её студенты."""
    model = Group
    template_name = 'contingent/group_detail.html'
    context_object_name = 'group'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['students'] = self.object.students.select_related('specialty').order_by('last_name', 'first_name')
        return ctx


class GroupDeleteView(DeleteView):
    """Удаление группы (запрещено, пока в группе есть студенты)."""
    model = Group
    template_name = 'contingent/group_confirm_delete.html'
    success_url = reverse_lazy('contingent:group_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['students_count'] = self.object.students.count()
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.students.exists():
            messages.error(
                request,
                f'Группу «{self.object.name}» нельзя удалить: в ней {self.object.students.count()} '
                'студентов. Сначала переведите или отчислите их.'
            )
            return redirect('contingent:group_detail', pk=self.object.pk)
        return super().post(request, *args, **kwargs)


# ---------------- Приказы ----------------

class OrderListView(ListView):
    model = Order
    template_name = 'contingent/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        return (Order.objects.select_related('order_type')
                             .prefetch_related('items')
                             .order_by('-date', '-number'))


class OrderCreateView(CreateView):
    """Создание приказа: реквизиты + формсет пунктов (студенты и действия)."""
    model = Order
    form_class = OrderForm
    template_name = 'contingent/order_form.html'
    success_url = reverse_lazy('contingent:order_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['formset'] = OrderItemFormSet(self.request.POST)
        else:
            ctx['formset'] = OrderItemFormSet(queryset=OrderItem.objects.none())
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx['formset']
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form))
        self.object = form.save()
        formset.instance = self.object
        formset.save()
        messages.success(self.request, f'Приказ №{self.object.number} сохранён.')
        return redirect('contingent:order_detail', pk=self.object.pk)


class OrderDetailView(DetailView):
    model = Order
    template_name = 'contingent/order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = self.object.items.select_related('student', 'group_to', 'group_from')
        return ctx


class OrderPostView(View):
    """Проведение приказа: обновление статусов + запись журнала движения."""

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        try:
            result = post_order(order)
            messages.success(request, f'Приказ проведён. {result}')
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect('contingent:order_detail', pk=order.pk)
