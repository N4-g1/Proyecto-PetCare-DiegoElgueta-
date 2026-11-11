# PetCare · Gestión clínica veterinaria

**Proyecto:** Proyecto PetCare DiegoElgueta  
**Desarrollado por:** Diego Alfredo Elgueta González  
**Asignatura:** Desarrollo Backend - Evaluación Parcial N°3 (PetCare)  
**Año:** 2026  
**IP Pública AWS EC2:** [http://54.226.155.169/](http://54.226.155.169/)  
**Django Admin AWS:** [http://54.226.155.169/admin/](http://54.226.155.169/admin/)

Aplicación Django en español para administrar tutores, mascotas, agenda médica, fichas clínicas y recordatorios preventivos. Incluye inicio de sesión, sesiones seguras, panel Django Admin personalizado y persistencia relacional en PostgreSQL para producción.

## Requisitos

- Python 3.10 o superior
- Desarrollo local: SQLite incluido con Python
- Producción: PostgreSQL 14+ y un servidor Linux, por ejemplo AWS EC2

## Puesta en marcha local (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
py manage.py migrate
py manage.py createsuperuser
py manage.py seed_demo
py manage.py runserver
```

Abre [http://127.0.0.1:8000](http://127.0.0.1:8000) e inicia sesión con la cuenta creada en `createsuperuser`. El entorno local usa SQLite. Crea y administra profesionales desde `/admin/`.

## PostgreSQL

Configura en `.env` o en las variables de entorno del servicio:

```dotenv
DJANGO_SECRET_KEY=una-clave-aleatoria-larga-y-privada
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=petcare.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://petcare.example.com
DJANGO_SECURE_COOKIES=True
DJANGO_SECURE_SSL_REDIRECT=True
DB_ENGINE=postgresql
DB_NAME=petcare
DB_USER=petcare_app
DB_PASSWORD=una-contraseña-segura
DB_HOST=127.0.0.1
DB_PORT=5432
DB_SSLMODE=require
```

Cuando `DJANGO_DEBUG=False`, el proyecto exige PostgreSQL, clave secreta y los parámetros principales de conexión. En una instancia EC2 con PostgreSQL local, mantén el puerto 5432 ligado a localhost y no lo abras en el security group. Para RDS o una instancia PostgreSQL independiente, usa su endpoint privado, habilita TLS y permite conexiones solo desde el grupo de seguridad de la aplicación.

Antes de arrancar la aplicación en producción:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
gunicorn petcare.wsgi:application --bind 127.0.0.1:8000
```

El procedimiento completo de PostgreSQL, EC2, Nginx y Gunicorn está en [docs/aws-ec2.md](docs/aws-ec2.md).

## Módulos

- **Tutores y mascotas:** altas, búsquedas, edición y eliminación protegida si existe historial clínico.
- **Agenda:** asignación por profesional, horarios configurables, jornadas semanales, duración y validación de citas cruzadas, pasadas o fuera de jornada.
- **Fichas clínicas:** historial con diagnósticos, tratamientos, recetas, exámenes y notas.
- **Recordatorios:** vacunas y controles; identifica los seguimientos vencidos y permite registrar su cumplimiento.
- **Administración:** `/admin/`, con filtros, búsquedas, jerarquía de fechas y selección de relaciones optimizada.

## Usuarios y Credenciales del Sistema

| Nombre Completo | Usuario | Contraseña | Rol / Función |
|---|---|---|---|
| **Diego Elgueta** | `admin` | `admin123` | Administrador general (Superusuario) |
| **Dra. Sofía Méndez** | `dra.sofia` | `petcare123` | Médico Veterinario (Medicina General) |
| **Dr. Tomás Herrera** | `dr.tomas` | `petcare123` | Médico Veterinario (Dermatología) |
| **Dra. Paula Silva** | `dra.paula` | `petcare123` | Médico Veterinario (Cirugía y Control) |
| **Camila Rojas** | `recepcionista1` | `petcare123` | Recepción y Agendamiento de Citas |
| **Matías Pérez** | `asistente1` | `petcare123` | Asistente Clínico |

Las pantallas de la clínica requieren una cuenta autenticada. El administrador crea las cuentas del personal desde Django Admin; no hay autorregistro público. El cierre de sesión utiliza una solicitud POST protegida por CSRF. Las notificaciones se gestionan dentro de la plataforma; el envío externo por correo o SMS no está implementado.

## Migraciones y comprobaciones

```powershell
py manage.py makemigrations clinic
py manage.py migrate
py manage.py check
py manage.py test clinic
```

No ejecutes `seed_demo` en producción: ese comando crea datos de ejemplo para la demostración local.
