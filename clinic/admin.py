from django.contrib import admin
from django.db.models import Count

from .models import Appointment, MedicalRecord, Pet, Reminder, Tutor, Veterinarian


@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "pet_count", "created_at")
    search_fields = ("name", "phone", "email")
    readonly_fields = ("created_at",)
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_pet_count=Count("pets"))

    @admin.display(description="Mascotas")
    def pet_count(self, obj):
        return obj._pet_count


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "species_detail", "breed", "tutor", "weight")
    list_filter = ("species", "sex")
    search_fields = ("name", "breed", "tutor__name", "tutor__phone")
    autocomplete_fields = ("tutor",)
    list_select_related = ("tutor",)


@admin.register(Veterinarian)
class VeterinarianAdmin(admin.ModelAdmin):
    list_display = ("name", "specialty", "active")
    list_filter = ("active", "specialty")
    search_fields = ("name", "specialty")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("date", "time", "pet", "veterinarian", "duration_minutes", "status")
    list_filter = ("date", "status", "veterinarian")
    search_fields = ("pet__name", "pet__tutor__name", "veterinarian__name", "reason")
    date_hierarchy = "date"
    autocomplete_fields = ("pet", "veterinarian")
    list_select_related = ("pet", "veterinarian")


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("date", "pet", "veterinarian", "diagnosis")
    list_filter = ("date",)
    search_fields = ("pet__name", "pet__tutor__name", "veterinarian", "diagnosis", "treatment")
    date_hierarchy = "date"
    autocomplete_fields = ("pet", "appointment")
    list_select_related = ("pet", "appointment")


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ("kind", "pet", "due_date", "status", "overdue")
    list_filter = ("status", "due_date", "kind")
    search_fields = ("kind", "pet__name", "pet__tutor__name")
    date_hierarchy = "due_date"
    autocomplete_fields = ("pet",)
    list_select_related = ("pet",)

    @admin.display(boolean=True, description="Atrasado")
    def overdue(self, obj):
        return obj.is_overdue


admin.site.site_header = "PetCare · Administración clínica"
admin.site.site_title = "PetCare Admin"
admin.site.index_title = "Operación veterinaria"
