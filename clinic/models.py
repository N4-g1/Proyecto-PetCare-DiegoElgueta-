from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator


class Tutor(models.Model):
    name = models.CharField("nombre completo", max_length=120)
    phone = models.CharField("teléfono", max_length=32)
    email = models.EmailField("correo electrónico", blank=True)
    address = models.CharField("dirección", max_length=220, blank=True)
    created_at = models.DateTimeField("registrado", auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "tutor"
        verbose_name_plural = "tutores"

    def __str__(self):
        return self.name


class Pet(models.Model):
    class Species(models.TextChoices):
        DOG = "Perro", "Perro"
        CAT = "Gato", "Gato"
        OTHER = "Otro", "Otro"

    class Sex(models.TextChoices):
        FEMALE = "Hembra", "Hembra"
        MALE = "Macho", "Macho"
        UNSPECIFIED = "No especificado", "No especificado"

    tutor = models.ForeignKey(Tutor, on_delete=models.PROTECT, related_name="pets", verbose_name="tutor")
    name = models.CharField("nombre", max_length=100)
    species = models.CharField("especie", max_length=20, choices=Species.choices)
    species_detail = models.CharField("tipo de animal", max_length=60, blank=True)
    breed = models.CharField("raza", max_length=100, blank=True)
    birthdate = models.DateField("fecha de nacimiento", null=True, blank=True)
    sex = models.CharField("sexo", max_length=24, choices=Sex.choices, blank=True)
    weight = models.DecimalField(
        "peso (kg)", max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    notes = models.TextField("notas clínicas", blank=True)
    created_at = models.DateTimeField("registrada", auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "mascota"
        verbose_name_plural = "mascotas"
        indexes = [models.Index(fields=["name", "species"], name="clinic_pet_name_species")]

    def __str__(self):
        species = self.species_detail if self.species == self.Species.OTHER and self.species_detail else self.get_species_display()
        return f"{self.name} · {species}"

    def clean(self):
        super().clean()
        detail = (self.species_detail or "").strip()
        if self.species == self.Species.OTHER and not detail:
            raise ValidationError({"species_detail": "Indica qué tipo de animal es."})
        if self.species != self.Species.OTHER and detail:
            raise ValidationError({"species_detail": "Este campo solo se completa cuando la especie es «Otro»."})
        self.species_detail = detail


class Veterinarian(models.Model):
    name = models.CharField("nombre", max_length=120)
    specialty = models.CharField("especialidad", max_length=100)
    schedule = models.JSONField(
        "disponibilidad semanal",
        default=dict,
        help_text='Días ISO [0-6] (lunes=0) y jornada, por ejemplo {"days":[0,1,2,3,4],"start":"09:00","end":"18:00"}.',
    )
    active = models.BooleanField("activo", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "profesional veterinario"
        verbose_name_plural = "profesionales veterinarios"

    def __str__(self):
        return f"{self.name} · {self.specialty}"

    def clean(self):
        super().clean()
        try:
            days = self.schedule["days"]
            start = datetime.strptime(self.schedule["start"], "%H:%M").time()
            end = datetime.strptime(self.schedule["end"], "%H:%M").time()
            if (
                not isinstance(days, list) or not days or any(day not in range(7) for day in days)
                or start >= end or start.minute not in (0, 30) or end.minute not in (0, 30)
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise ValidationError({"schedule": "Indica días ISO válidos y un horario de inicio anterior al de cierre."})

    def works_on(self, day):
        return self.active and isinstance(self.schedule, dict) and day.weekday() in self.schedule.get("days", [])


class Appointment(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "Confirmada", "Confirmada"
        WAITING = "En espera", "En espera"
        COMPLETED = "Completada", "Completada"
        CANCELLED = "Cancelada", "Cancelada"

    class Duration(models.IntegerChoices):
        MINUTES_30 = 30, "30 minutos"
        MINUTES_45 = 45, "45 minutos"
        MINUTES_60 = 60, "60 minutos"
        MINUTES_90 = 90, "90 minutos"

    pet = models.ForeignKey(Pet, on_delete=models.PROTECT, related_name="appointments", verbose_name="mascota")
    veterinarian = models.ForeignKey(Veterinarian, on_delete=models.PROTECT, related_name="appointments", verbose_name="profesional")
    date = models.DateField("fecha")
    time = models.TimeField("hora")
    duration_minutes = models.PositiveSmallIntegerField(
        "duración (minutos)", choices=Duration.choices, default=Duration.MINUTES_30,
    )
    reason = models.CharField("motivo de consulta", max_length=220)
    status = models.CharField("estado", max_length=16, choices=Status.choices, default=Status.CONFIRMED)
    created_at = models.DateTimeField("creada", auto_now_add=True)

    class Meta:
        ordering = ["date", "time"]
        verbose_name = "cita"
        verbose_name_plural = "citas"
        indexes = [models.Index(fields=["date", "veterinarian", "status"], name="clinic_appt_day_vet_status")]

    def __str__(self):
        return f"{self.pet.name} · {self.date:%d-%m-%Y} {self.time:%H:%M}"

    def clean(self):
        super().clean()
        errors = {}
        if not self.date or not self.time or not self.veterinarian_id:
            return
        if self.date < timezone.localdate():
            errors["date"] = "No se pueden agendar citas en una fecha pasada."
        elif self.date == timezone.localdate() and timezone.is_aware(timezone.now()):
            local_time = timezone.localtime().time().replace(second=0, microsecond=0)
            if self.time <= local_time:
                errors["time"] = "Selecciona un horario futuro."
        if self.duration_minutes not in Appointment.Duration.values:
            errors["duration_minutes"] = "Selecciona una duración entre las opciones disponibles."
        if self.time.minute not in (0, 30):
            errors["time"] = "La agenda utiliza bloques de 30 minutos."

        veterinarian = self.veterinarian
        schedule = veterinarian.schedule
        start = datetime.combine(self.date, self.time)
        end = start + timedelta(minutes=self.duration_minutes or 0)
        try:
            opening = datetime.strptime(schedule["start"], "%H:%M").time()
            closing = datetime.strptime(schedule["end"], "%H:%M").time()
            if not veterinarian.works_on(self.date) or self.time < opening or end.time() > closing or end.date() != self.date:
                errors["time"] = "El profesional no está disponible en ese día u horario."
        except (KeyError, TypeError, ValueError):
            errors["veterinarian"] = "La disponibilidad del profesional no está configurada correctamente."

        if self.status != self.Status.CANCELLED:
            conflicts = Appointment.objects.filter(
                veterinarian_id=self.veterinarian_id,
                date=self.date,
            ).exclude(status=self.Status.CANCELLED)
            if self.pk:
                conflicts = conflicts.exclude(pk=self.pk)
            for existing in conflicts.only("date", "time", "duration_minutes"):
                other_start = datetime.combine(existing.date, existing.time)
                other_end = other_start + timedelta(minutes=existing.duration_minutes)
                if start < other_end and other_start < end:
                    errors["time"] = f"El profesional ya tiene una cita que se cruza con las {existing.time:%H:%M}."
                    break
        if errors:
            raise ValidationError(errors)


class MedicalRecord(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.PROTECT, related_name="medical_records", verbose_name="mascota")
    appointment = models.OneToOneField(
        Appointment, on_delete=models.SET_NULL, related_name="medical_record", verbose_name="cita relacionada",
        null=True, blank=True,
    )
    date = models.DateField("fecha de atención", default=timezone.localdate)
    veterinarian = models.CharField("profesional responsable", max_length=120)
    diagnosis = models.TextField("diagnóstico")
    treatment = models.TextField("tratamiento", blank=True)
    prescription = models.TextField("receta médica", blank=True)
    exams = models.TextField("exámenes", blank=True)
    notes = models.TextField("notas y seguimiento", blank=True)
    created_at = models.DateTimeField("creada", auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "ficha clínica"
        verbose_name_plural = "fichas clínicas"
        indexes = [models.Index(fields=["pet", "-date"], name="clinic_record_pet_date")]

    def __str__(self):
        return f"{self.pet.name} · {self.date:%d-%m-%Y}"


class Reminder(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pendiente", "Pendiente"
        COMPLETED = "Completado", "Completado"

    pet = models.ForeignKey(Pet, on_delete=models.PROTECT, related_name="reminders", verbose_name="mascota")
    kind = models.CharField("vacuna o control", max_length=160)
    due_date = models.DateField("fecha programada")
    notes = models.TextField("notas", blank=True)
    status = models.CharField("estado", max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        ordering = ["due_date", "kind"]
        verbose_name = "recordatorio preventivo"
        verbose_name_plural = "recordatorios preventivos"
        indexes = [models.Index(fields=["status", "due_date"], name="clinic_rem_status_due")]

    def __str__(self):
        return f"{self.kind} · {self.pet.name}"

    @property
    def is_overdue(self):
        return self.status == self.Status.PENDING and self.due_date < timezone.localdate()
