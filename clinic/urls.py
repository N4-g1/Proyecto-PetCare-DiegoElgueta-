from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import (
    AppointmentCreateView,
    AppointmentListView,
    AppointmentUpdateView,
    AvailabilityView,
    CreateClinicRecord,
    DashboardView,
    MedicalRecordListView,
    MODEL_CONFIG,
    PetListView,
    ReminderListView,
    SafeDeleteClinicRecord,
    StaffLoginView,
    TutorListView,
    UpdateClinicRecord,
)


def crud_patterns(key, config):
    create_view = AppointmentCreateView if key == "appointments" else CreateClinicRecord
    update_view = AppointmentUpdateView if key == "appointments" else UpdateClinicRecord
    return [
        path(f"{key}/nuevo/", create_view.as_view(model=config["model"], form_class=config["form"], config_key=key), name=f"{key}_create"),
        path(f"{key}/<int:pk>/editar/", update_view.as_view(model=config["model"], form_class=config["form"], config_key=key), name=f"{key}_update"),
        path(f"{key}/<int:pk>/eliminar/", SafeDeleteClinicRecord.as_view(model=config["model"], config_key=key), name=f"{key}_delete"),
    ]

urlpatterns = [
    path("accounts/login/", StaffLoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("", DashboardView.as_view(), name="dashboard"),
    path("tutores/", TutorListView.as_view(), name="tutors_list"),
    path("mascotas/", PetListView.as_view(), name="pets_list"),
    path("agenda/", AppointmentListView.as_view(), name="appointments_list"),
    path("fichas/", MedicalRecordListView.as_view(), name="records_list"),
    path("recordatorios/", ReminderListView.as_view(), name="reminders_list"),
    path("disponibilidad/", AvailabilityView.as_view(), name="availability"),
] + [route for key, config in MODEL_CONFIG.items() for route in crud_patterns(key, config)]
