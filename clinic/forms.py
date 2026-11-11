from datetime import datetime, time

from django import forms
from django.utils import timezone

from .models import Appointment, MedicalRecord, Pet, Reminder, Tutor


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            widget.attrs.setdefault("class", "form-control")
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", 3)
                widget.attrs.setdefault("placeholder", "Escribe aquí…")


class TutorForm(StyledModelForm):
    class Meta:
        model = Tutor
        fields = ["name", "phone", "email", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }


class PetForm(StyledModelForm):
    class Meta:
        model = Pet
        fields = ["tutor", "name", "species", "species_detail", "breed", "birthdate", "sex", "weight", "notes"]
        widgets = {
            "species_detail": forms.TextInput(attrs={"placeholder": "Por ejemplo: conejo, tortuga, ave…"}),
            "birthdate": forms.DateInput(attrs={"type": "date"}),
            "weight": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["species_detail"].required = False
        self.fields["species_detail"].widget.attrs.update({
            "data-species-detail": "true",
            "maxlength": "60",
        })

    def clean(self):
        cleaned_data = super().clean()
        species = cleaned_data.get("species")
        species_detail = (cleaned_data.get("species_detail") or "").strip()
        if species == Pet.Species.OTHER and not species_detail:
            self.add_error("species_detail", "Indica qué tipo de animal es.")
        elif species != Pet.Species.OTHER:
            cleaned_data["species_detail"] = ""
        return cleaned_data


class AppointmentForm(StyledModelForm):
    time = forms.ChoiceField(label="Hora", choices=(), widget=forms.Select())

    class Meta:
        model = Appointment
        fields = ["pet", "veterinarian", "date", "time", "duration_minutes", "reason", "status"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}), "duration_minutes": forms.Select()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        slots = [
            (
                time(hour=hour, minute=minute).strftime("%H:%M"),
                time(hour=hour, minute=minute).strftime("%H:%M"),
            )
            for hour in range(9, 18)
            for minute in (0, 30)
        ]
        self.fields["time"].choices = [("", "Selecciona un horario disponible"), *slots]
        self.fields["date"].widget.attrs["min"] = timezone.localdate().isoformat()
        self.fields["veterinarian"].queryset = self.fields["veterinarian"].queryset.filter(active=True)

    def clean_time(self):
        value = self.cleaned_data["time"]
        return datetime.strptime(value, "%H:%M").time()


class MedicalRecordForm(StyledModelForm):
    class Meta:
        model = MedicalRecord
        fields = ["pet", "appointment", "date", "veterinarian", "diagnosis", "treatment", "prescription", "exams", "notes"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class ReminderForm(StyledModelForm):
    class Meta:
        model = Reminder
        fields = ["pet", "kind", "due_date", "notes", "status"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}
