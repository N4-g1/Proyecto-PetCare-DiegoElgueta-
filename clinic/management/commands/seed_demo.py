from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from clinic.models import Appointment, MedicalRecord, Pet, Reminder, Tutor, Veterinarian


class Command(BaseCommand):
    help = "Crea registros de ejemplo para recorrer la aplicación localmente."

    def handle(self, *args, **options):
        veterinarians = [
            ("Dra. Sofía Méndez", "Medicina general", {"days": [0, 1, 2, 3, 4], "start": "09:00", "end": "18:00"}),
            ("Dr. Tomás Herrera", "Dermatología", {"days": [0, 1, 2, 3, 4, 5], "start": "10:00", "end": "17:00"}),
            ("Dra. Paula Silva", "Cirugía y control", {"days": [1, 2, 3, 4, 5], "start": "09:00", "end": "16:00"}),
        ]
        vet_objects = {
            name: Veterinarian.objects.update_or_create(
                name=name, defaults={"specialty": specialty, "schedule": schedule, "active": True}
            )[0]
            for name, specialty, schedule in veterinarians
        }
        tutor_data = [
            ("Camila Rojas", "+56 9 6123 4587", "camila.rojas@email.com", "Providencia, Santiago"),
            ("Matías Fuentes", "+56 9 7345 2190", "matias.f@email.com", "Ñuñoa, Santiago"),
            ("Valentina Soto", "+56 9 8562 1034", "vale.soto@email.com", "Las Condes, Santiago"),
        ]
        tutors = {
            name: Tutor.objects.update_or_create(
                name=name, defaults={"phone": phone, "email": email, "address": address}
            )[0]
            for name, phone, email, address in tutor_data
        }
        pet_data = [
            ("Luna", "Perro", "Golden Retriever", "2021-06-15", "Hembra", "24.50", tutors["Camila Rojas"]),
            ("Milo", "Gato", "Mestizo", "2022-10-04", "Macho", "5.20", tutors["Matías Fuentes"]),
            ("Nala", "Perro", "Beagle", "2020-03-21", "Hembra", "12.80", tutors["Valentina Soto"]),
            ("Simba", "Gato", "Persa", "2023-01-11", "Macho", "4.10", tutors["Camila Rojas"]),
        ]
        pets = {
            name: Pet.objects.update_or_create(
                name=name, tutor=tutor,
                defaults={
                    "species": species, "breed": breed, "birthdate": birthdate,
                    "sex": sex, "weight": weight,
                },
            )[0]
            for name, species, breed, birthdate, sex, weight, tutor in pet_data
        }
        today = timezone.localdate()
        next_weekday = today
        while next_weekday.weekday() > 4 or (
            next_weekday == today and timezone.localtime().time().replace(second=0, microsecond=0) >= time(9)
        ):
            next_weekday += timedelta(days=1)

        appointments = [
            (pets["Luna"], vet_objects["Dra. Sofía Méndez"], next_weekday, "09:00", 30, "Control anual"),
            (pets["Milo"], vet_objects["Dr. Tomás Herrera"], next_weekday, "10:30", 45, "Consulta dermatológica"),
            (pets["Nala"], vet_objects["Dra. Sofía Méndez"], next_weekday, "12:00", 30, "Vacunación"),
            (pets["Simba"], vet_objects["Dra. Paula Silva"], next_weekday + timedelta(days=1), "11:00", 45, "Control preventivo"),
        ]
        for pet, veterinarian, day, at, duration, reason in appointments:
            Appointment.objects.get_or_create(
                pet=pet, veterinarian=veterinarian, date=day, time=at,
                defaults={"duration_minutes": duration, "reason": reason},
            )

        MedicalRecord.objects.get_or_create(
            pet=pets["Luna"], date=today - timedelta(days=30),
            defaults={
                "veterinarian": "Dra. Sofía Méndez",
                "diagnosis": "Paciente en buen estado general",
                "treatment": "Control de rutina y evaluación dental",
                "prescription": "Antiparasitario oral, según peso",
                "exams": "Hemograma sin alteraciones",
                "notes": "Repetir control en 6 meses",
            },
        )
        MedicalRecord.objects.get_or_create(
            pet=pets["Milo"], date=today - timedelta(days=14),
            defaults={
                "veterinarian": "Dr. Tomás Herrera", "diagnosis": "Dermatitis leve",
                "treatment": "Limpieza de zona afectada",
                "prescription": "Champú dermatológico 2 veces por semana",
                "notes": "Evaluar evolución en 14 días",
            },
        )
        reminders = [
            (pets["Luna"], "Vacunación antirrábica", today + timedelta(days=3), "Refuerzo anual"),
            (pets["Milo"], "Control dermatológico", today + timedelta(days=1), "Revisar respuesta al tratamiento"),
            (pets["Nala"], "Vacuna óctuple", today - timedelta(days=2), "Refuerzo anual"),
            (pets["Simba"], "Desparasitación", today + timedelta(days=12), "Control preventivo"),
        ]
        for pet, kind, due_date, notes in reminders:
            Reminder.objects.get_or_create(
                pet=pet, kind=kind, due_date=due_date,
                defaults={"notes": notes},
            )
        self.stdout.write(self.style.SUCCESS("Datos de demostración creados o actualizados."))
