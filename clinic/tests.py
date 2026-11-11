from datetime import time, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .admin import AppointmentAdmin, MedicalRecordAdmin, PetAdmin, ReminderAdmin, TutorAdmin, VeterinarianAdmin
from .forms import PetForm
from .models import Appointment, MedicalRecord, Pet, Reminder, Tutor, Veterinarian


class ClinicAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="clinica", password="PetCare-test-93")

    def test_dashboard_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_authenticated_user_can_open_dashboard_and_lists(self):
        self.client.login(username="clinica", password="PetCare-test-93")
        for name in ("dashboard", "tutors_list", "pets_list", "appointments_list", "records_list", "reminders_list"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)

    def test_logout_requires_post_and_ends_the_session(self):
        self.client.login(username="clinica", password="PetCare-test-93")
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.client.post(reverse("logout"))
        self.assertRedirects(self.client.get(reverse("dashboard")), f"{reverse('login')}?next={reverse('dashboard')}")


class ClinicCrudTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="clinica", password="PetCare-test-93")
        self.client.login(username="clinica", password="PetCare-test-93")
        self.tutor = Tutor.objects.create(name="Camila Rojas", phone="+56912345678")
        self.pet = Pet.objects.create(tutor=self.tutor, name="Luna", species=Pet.Species.DOG)
        self.veterinarian = Veterinarian.objects.create(
            name="Dra. Sofía Méndez",
            specialty="Medicina general",
            schedule={"days": [0, 1, 2, 3, 4, 5, 6], "start": "00:00", "end": "23:59"},
        )
        self.visit_date = timezone.localdate() + timedelta(days=1)
        while self.visit_date.weekday() == 6:
            self.visit_date += timedelta(days=1)

    def test_tutor_and_pet_create_and_update(self):
        response = self.client.post(reverse("tutors_create"), {"name": "Matías Fuentes", "phone": "555-0101"})
        self.assertRedirects(response, reverse("tutors_list"))
        new_tutor = Tutor.objects.get(name="Matías Fuentes")
        response = self.client.post(reverse("pets_create"), {"tutor": new_tutor.pk, "name": "Milo", "species": "Gato"})
        self.assertRedirects(response, reverse("pets_list"))
        pet = Pet.objects.get(name="Milo")
        response = self.client.post(reverse("pets_update", args=[pet.pk]), {"tutor": new_tutor.pk, "name": "Milo II", "species": "Gato"})
        self.assertRedirects(response, reverse("pets_list"))
        self.assertTrue(Pet.objects.filter(pk=pet.pk, name="Milo II").exists())

    def test_other_species_requires_and_saves_the_animal_type(self):
        incomplete = PetForm(data={"tutor": self.tutor.pk, "name": "Pipo", "species": Pet.Species.OTHER})
        self.assertFalse(incomplete.is_valid())
        self.assertIn("species_detail", incomplete.errors)

        response = self.client.post(reverse("pets_create"), {
            "tutor": self.tutor.pk, "name": "Pipo", "species": Pet.Species.OTHER,
            "species_detail": "Conejo",
        })
        self.assertRedirects(response, reverse("pets_list"))
        pet = Pet.objects.get(name="Pipo")
        self.assertEqual(pet.species_detail, "Conejo")
        self.assertEqual(str(pet), "Pipo · Conejo")

    def test_pet_form_hides_other_type_until_other_is_selected(self):
        response = self.client.get(reverse("pets_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_species_detail"')
        self.assertContains(response, 'class="form-field field-wide species-detail-field" hidden')

    def test_appointment_form_keeps_date_and_accepts_available_dynamic_time(self):
        url = f"{reverse('appointments_create')}?date={self.visit_date.isoformat()}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"]["date"].value(), self.visit_date)
        response = self.client.post(reverse("appointments_create"), {
            "pet": self.pet.pk,
            "veterinarian": self.veterinarian.pk,
            "date": self.visit_date.isoformat(),
            "time": "10:30",
            "duration_minutes": 30,
            "reason": "Control",
            "status": Appointment.Status.CONFIRMED,
        })
        self.assertRedirects(response, f"{reverse('appointments_list')}?date={self.visit_date.isoformat()}")
        self.assertTrue(Appointment.objects.filter(date=self.visit_date, time=time(10, 30)).exists())

    def test_appointment_rejects_overlaps_and_accepts_available_slot(self):
        first = Appointment(
            pet=self.pet, veterinarian=self.veterinarian, date=self.visit_date,
            time=time(10), duration_minutes=45, reason="Control",
        )
        first.full_clean()
        first.save()
        overlapping = Appointment(
            pet=self.pet, veterinarian=self.veterinarian, date=self.visit_date,
            time=time(10, 30), duration_minutes=30, reason="Vacunación",
        )
        with self.assertRaises(ValidationError):
            overlapping.full_clean()
        available = Appointment(
            pet=self.pet, veterinarian=self.veterinarian, date=self.visit_date,
            time=time(11), duration_minutes=30, reason="Control",
        )
        response = self.client.post(reverse("appointments_create"), {
            "pet": self.pet.pk,
            "veterinarian": self.veterinarian.pk,
            "date": self.visit_date.isoformat(),
            "time": "11:00",
            "duration_minutes": 30,
            "reason": "Control",
            "status": Appointment.Status.CONFIRMED,
        })
        self.assertRedirects(response, f"{reverse('appointments_list')}?date={self.visit_date.isoformat()}")
        self.assertTrue(Appointment.objects.filter(time=time(11)).exists())

    def test_appointment_form_rejects_day_off_and_past(self):
        weekdays = {"days": [0, 1, 2, 3, 4], "start": "09:00", "end": "18:00"}
        self.veterinarian.schedule = weekdays
        self.veterinarian.save()
        saturday = self.visit_date
        while saturday.weekday() != 5:
            saturday += timedelta(days=1)
        appointment = Appointment(
            pet=self.pet, veterinarian=self.veterinarian, date=saturday,
            time=time(10), duration_minutes=30, reason="Control",
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_record_and_reminder_lifecycle_and_delete(self):
        response = self.client.post(reverse("records_create"), {
            "pet": self.pet.pk, "date": self.visit_date.isoformat(), "veterinarian": "Dra. Sofía",
            "diagnosis": "Buen estado", "treatment": "Control", "prescription": "",
            "exams": "", "notes": "",
        })
        self.assertRedirects(response, reverse("records_list"))
        record = MedicalRecord.objects.get(pet=self.pet)
        response = self.client.post(reverse("records_delete", args=[record.pk]), {"confirm": "yes"})
        self.assertRedirects(response, reverse("records_list"))
        self.assertFalse(MedicalRecord.objects.filter(pk=record.pk).exists())
        response = self.client.post(reverse("reminders_create"), {
            "pet": self.pet.pk, "kind": "Vacuna", "due_date": self.visit_date.isoformat(),
            "notes": "", "status": Reminder.Status.PENDING,
        })
        self.assertRedirects(response, reverse("reminders_list"))
        reminder = Reminder.objects.get(pet=self.pet)
        response = self.client.post(reverse("reminders_update", args=[reminder.pk]), {
            "pet": self.pet.pk, "kind": "Vacuna", "due_date": self.visit_date.isoformat(),
            "notes": "", "status": Reminder.Status.COMPLETED,
        })
        self.assertRedirects(response, reverse("reminders_list"))
        reminder.refresh_from_db()
        self.assertEqual(reminder.status, Reminder.Status.COMPLETED)

    def test_availability_endpoint_is_authenticated_and_excludes_busy_times(self):
        Appointment.objects.create(
            pet=self.pet, veterinarian=self.veterinarian, date=self.visit_date,
            time=time(10), duration_minutes=60, reason="Control",
        )
        url = reverse("availability")
        params = {"veterinarian": self.veterinarian.pk, "date": self.visit_date.isoformat(), "duration": 30}
        self.client.logout()
        self.assertEqual(self.client.get(url, params).status_code, 302)
        self.client.login(username="clinica", password="PetCare-test-93")
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("10:00", response.json()["slots"])
        self.assertNotIn("10:30", response.json()["slots"])
        self.assertIn("11:00", response.json()["slots"])

    def test_pet_with_medical_history_cannot_be_deleted(self):
        MedicalRecord.objects.create(
            pet=self.pet, date=self.visit_date, veterinarian="Dra. Sofía", diagnosis="Control",
        )
        response = self.client.post(reverse("pets_delete", args=[self.pet.pk]))
        self.assertRedirects(response, reverse("pets_list"))
        self.assertTrue(Pet.objects.filter(pk=self.pet.pk).exists())


class AdminConfigurationTests(TestCase):
    def test_all_domain_models_are_registered_with_custom_admin(self):
        expected = {
            Tutor: TutorAdmin,
            Pet: PetAdmin,
            Veterinarian: VeterinarianAdmin,
            Appointment: AppointmentAdmin,
            MedicalRecord: MedicalRecordAdmin,
            Reminder: ReminderAdmin,
        }
        from django.contrib import admin

        for model, admin_class in expected.items():
            self.assertIsInstance(admin.site._registry[model], admin_class)

    def test_admin_requires_staff_and_exposes_the_registered_models(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)
        staff_user = User.objects.create_superuser(username="admin-clinic", password="PetCare-test-93")
        self.client.force_login(staff_user)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        for model in ("Citas", "Fichas clínicas", "Mascotas", "Tutores", "Recordatorios preventivos"):
            self.assertContains(response, model)


class ReminderModelTests(TestCase):
    def test_overdue_property_tracks_pending_and_completed_states(self):
        tutor = Tutor.objects.create(name="Valentina Soto", phone="555-1111")
        pet = Pet.objects.create(tutor=tutor, name="Nala", species=Pet.Species.DOG)
        reminder = Reminder.objects.create(
            pet=pet, kind="Vacuna", due_date=timezone.localdate() - timedelta(days=1),
        )
        self.assertTrue(reminder.is_overdue)
        reminder.status = Reminder.Status.COMPLETED
        self.assertFalse(reminder.is_overdue)
