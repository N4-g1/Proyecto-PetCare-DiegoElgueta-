from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .forms import AppointmentForm, MedicalRecordForm, PetForm, ReminderForm, TutorForm
from .models import Appointment, MedicalRecord, Pet, Reminder, Tutor, Veterinarian


MODEL_CONFIG = {
    "tutors": {
        "model": Tutor, "form": TutorForm, "title": "Tutores", "singular": "tutor",
        "new_label": "Nuevo tutor",
        "description": "Un directorio claro para las familias que confían en la clínica.",
        "columns": ("Tutor", "Contacto", "Correo electrónico", "Mascotas"), "search": "Nombre, teléfono o correo",
    },
    "pets": {
        "model": Pet, "form": PetForm, "title": "Mascotas", "singular": "mascota",
        "new_label": "Nueva mascota",
        "description": "El perfil y los cuidados importantes de cada paciente.",
        "columns": ("Paciente", "Especie y raza", "Tutor responsable", "Peso"), "search": "Nombre, especie o tutor",
    },
    "appointments": {
        "model": Appointment, "form": AppointmentForm, "title": "Agenda médica", "singular": "cita",
        "new_label": "Nueva cita",
        "description": "La jornada del equipo, organizada por profesional y disponibilidad.",
        "columns": ("Hora", "Paciente", "Profesional", "Motivo", "Estado"), "search": "Paciente, tutor o motivo",
    },
    "records": {
        "model": MedicalRecord, "form": MedicalRecordForm, "title": "Fichas clínicas", "singular": "ficha clínica",
        "new_label": "Nueva ficha clínica",
        "description": "Diagnósticos, tratamientos y seguimiento en un solo historial.",
        "columns": ("Paciente", "Fecha", "Profesional", "Diagnóstico"), "search": "Paciente, profesional o diagnóstico",
    },
    "reminders": {
        "model": Reminder, "form": ReminderForm, "title": "Recordatorios", "singular": "recordatorio",
        "new_label": "Nuevo recordatorio",
        "description": "Vacunación y controles preventivos que requieren seguimiento.",
        "columns": ("Seguimiento", "Paciente", "Fecha", "Tutor", "Estado"), "search": "Tipo, paciente o tutor",
    },
}


class StaffLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "clinic/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        local_hour = timezone.localtime().hour
        context.update({
            "today": today,
            "greeting": "Buenos días" if local_hour < 12 else "Buenas tardes" if local_hour < 19 else "Buenas noches",
            "greeting_name": self.request.user.first_name or "equipo",
            "tutor_count": Tutor.objects.count(),
            "pet_count": Pet.objects.count(),
            "appointment_count": Appointment.objects.filter(date=today).exclude(status=Appointment.Status.CANCELLED).count(),
            "pending_count": Reminder.objects.filter(status=Reminder.Status.PENDING).count(),
            "agenda_date": Appointment.objects.filter(
                date__gte=today
            ).exclude(status=Appointment.Status.CANCELLED).order_by("date", "time").values_list("date", flat=True).first() or today,
            "upcoming_reminders": Reminder.objects.filter(status=Reminder.Status.PENDING).select_related(
                "pet", "pet__tutor"
            ).order_by("due_date")[:6],
            "overdue_count": Reminder.objects.filter(
                status=Reminder.Status.PENDING, due_date__lt=today
            ).count(),
            "veterinarians": Veterinarian.objects.filter(active=True),
        })
        context["today_appointments"] = Appointment.objects.filter(date=context["agenda_date"]).exclude(
            status=Appointment.Status.CANCELLED
        ).select_related("pet", "pet__tutor", "veterinarian")
        return context


class ClinicListView(LoginRequiredMixin, ListView):
    template_name = "clinic/object_list.html"
    context_object_name = "items"
    paginate_by = 20
    config_key = ""

    def get_queryset(self):
        self.config = MODEL_CONFIG[self.config_key]
        queryset = self.config["model"].objects.all()
        if self.config_key == "tutors":
            queryset = queryset.annotate(pet_count=Count("pets")).order_by("name")
        elif self.config_key == "pets":
            queryset = queryset.select_related("tutor")
        elif self.config_key == "appointments":
            queryset = queryset.select_related("pet", "pet__tutor", "veterinarian")
            selected_date = self.request.GET.get("date", "")
            if selected_date:
                try:
                    queryset = queryset.filter(date=date.fromisoformat(selected_date))
                except ValueError:
                    selected_date = ""
            self.selected_date = selected_date or timezone.localdate().isoformat()
            queryset = queryset.filter(date=self.selected_date)
        elif self.config_key == "records":
            queryset = queryset.select_related("pet", "pet__tutor")
        elif self.config_key == "reminders":
            queryset = queryset.select_related("pet", "pet__tutor")
            status = self.request.GET.get("status", "")
            if status in Reminder.Status.values:
                queryset = queryset.filter(status=status)
            self.selected_status = status

        query = self.request.GET.get("q", "").strip()
        if query:
            search_fields = {
                "tutors": Q(name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query),
                "pets": Q(name__icontains=query) | Q(species__icontains=query) | Q(species_detail__icontains=query) | Q(breed__icontains=query) | Q(tutor__name__icontains=query),
                "appointments": Q(pet__name__icontains=query) | Q(pet__tutor__name__icontains=query) | Q(veterinarian__name__icontains=query) | Q(reason__icontains=query),
                "records": Q(pet__name__icontains=query) | Q(veterinarian__icontains=query) | Q(diagnosis__icontains=query),
                "reminders": Q(kind__icontains=query) | Q(pet__name__icontains=query) | Q(pet__tutor__name__icontains=query),
            }
            queryset = queryset.filter(search_fields[self.config_key])
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "config": self.config,
            "list_type": self.config_key,
            "query": self.request.GET.get("q", ""),
            "selected_date": getattr(self, "selected_date", ""),
            "today_date": timezone.localdate().isoformat(),
            "previous_date": (
                date.fromisoformat(self.selected_date) - timedelta(days=1)
                if self.config_key == "appointments" else None
            ),
            "next_date": (
                date.fromisoformat(self.selected_date) + timedelta(days=1)
                if self.config_key == "appointments" else None
            ),
            "selected_status": getattr(self, "selected_status", ""),
            "create_url": f"{self.config_key}_create",
        })
        return context


class TutorListView(ClinicListView):
    config_key = "tutors"


class PetListView(ClinicListView):
    config_key = "pets"


class AppointmentListView(ClinicListView):
    config_key = "appointments"


class MedicalRecordListView(ClinicListView):
    config_key = "records"


class ReminderListView(ClinicListView):
    config_key = "reminders"


class ClinicFormContextMixin:
    config_key = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["config"] = MODEL_CONFIG[self.config_key]
        context["list_url"] = f"{self.config_key}_list"
        context["list_type"] = self.config_key
        context["is_edit"] = self.request.resolver_match.url_name.endswith("_update")
        return context


class CreateClinicRecord(LoginRequiredMixin, ClinicFormContextMixin, CreateView):
    template_name = "clinic/object_form.html"
    success_message = "El registro se guardó correctamente."

    def get_initial(self):
        initial = super().get_initial()
        if self.config_key == "appointments":
            requested_date = self.request.GET.get("date", "")
            try:
                selected_date = date.fromisoformat(requested_date)
            except ValueError:
                selected_date = timezone.localdate()
            if selected_date >= timezone.localdate():
                initial["date"] = selected_date
        return initial

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(f"{self.config_key}_list")


class UpdateClinicRecord(LoginRequiredMixin, ClinicFormContextMixin, UpdateView):
    template_name = "clinic/object_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Los cambios se guardaron correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(f"{self.config_key}_list")


class SafeDeleteClinicRecord(LoginRequiredMixin, DeleteView):
    template_name = "clinic/object_confirm_delete.html"
    success_url = reverse_lazy("dashboard")
    config_key = ""

    def get_success_url(self):
        return reverse_lazy(f"{self.config_key}_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["config"] = MODEL_CONFIG[self.config_key]
        context["config_key"] = self.config_key
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "El registro se eliminó correctamente.")
            return response
        except ProtectedError:
            messages.error(self.request, "No se puede eliminar: todavía existen registros clínicos asociados.")
            return redirect(self.get_success_url())


class AppointmentSaveMixin:
    def form_valid(self, form):
        try:
            with transaction.atomic():
                Veterinarian.objects.select_for_update().get(pk=form.instance.veterinarian_id)
                self.object = form.save(commit=False)
                self.object.full_clean()
                self.object.save()
                form.save_m2m()
        except ValidationError as error:
            if hasattr(error, "message_dict"):
                for field, errors in error.message_dict.items():
                    form.add_error(field if field in form.fields else None, errors)
            else:
                form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "La cita se guardó correctamente.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        appointment_date = self.object.date.isoformat()
        return f"{reverse_lazy('appointments_list')}?date={appointment_date}"


class AppointmentCreateView(AppointmentSaveMixin, CreateClinicRecord):
    pass


class AppointmentUpdateView(AppointmentSaveMixin, UpdateClinicRecord):
    pass


@method_decorator(require_GET, name="dispatch")
class AvailabilityView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            veterinarian = Veterinarian.objects.get(pk=request.GET.get("veterinarian"), active=True)
            appointment_date = date.fromisoformat(request.GET.get("date", ""))
            duration = int(request.GET.get("duration", "30"))
            appointment_id = request.GET.get("appointment", "")
            if duration not in {30, 45, 60, 90}:
                raise ValueError
        except (Veterinarian.DoesNotExist, TypeError, ValueError):
            return JsonResponse({"error": "Selecciona un profesional, una fecha y una duración válidos."}, status=400)

        schedule = veterinarian.schedule
        if not veterinarian.works_on(appointment_date):
            return JsonResponse({"slots": []})
        try:
            opening = datetime.strptime(schedule["start"], "%H:%M").time()
            closing = datetime.strptime(schedule["end"], "%H:%M").time()
        except (KeyError, TypeError, ValueError):
            return JsonResponse({"error": "La disponibilidad del profesional no está configurada."}, status=400)
        busy = Appointment.objects.filter(
            veterinarian=veterinarian, date=appointment_date
        ).exclude(status=Appointment.Status.CANCELLED)
        if appointment_id.isdigit():
            busy = busy.exclude(pk=int(appointment_id))
        existing = [(entry.time, entry.duration_minutes) for entry in busy]
        current_time = timezone.localtime().time().replace(second=0, microsecond=0)
        slots = []
        cursor = datetime.combine(appointment_date, opening)
        close_at = datetime.combine(appointment_date, closing)
        while cursor + timedelta(minutes=duration) <= close_at:
            slot_time = cursor.time()
            slot_end = cursor + timedelta(minutes=duration)
            if appointment_date > timezone.localdate() or slot_time > current_time:
                overlaps = any(
                    cursor < datetime.combine(appointment_date, occupied_time) + timedelta(minutes=occupied_duration)
                    and datetime.combine(appointment_date, occupied_time) < slot_end
                    for occupied_time, occupied_duration in existing
                )
                if not overlaps:
                    slots.append(slot_time.strftime("%H:%M"))
            cursor += timedelta(minutes=30)
        return JsonResponse({"slots": slots})
