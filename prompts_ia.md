# Evidencia de Uso de IA — PetCare

- **Estudiante:** Diego Alfredo Elgueta González
- **Asignatura:** Desarrollo Backend - Evaluación 3
- **Proyecto:** PetCare

---

### Consultas Realizadas

#### 1. Modelos y Base de Datos
- **Consulta:** Estructura recomendada para modelos en Django con relaciones entre tutores, mascotas, citas médicas y fichas clínicas.
- **Uso:** Definición de campos, llaves foráneas y validaciones básicas en `clinic/models.py`.

#### 2. Lógica de Agenda y Validación de Citas
- **Consulta:** Cómo evitar solapamiento de horarios en citas veterinarias según el profesional asignado en Django.
- **Uso:** Implementación del método `clean()` en el formulario de citas para verificar disponibilidad horaria.

#### 3. Configuración de Despliegue en AWS EC2
- **Consulta:** Ejemplo de configuración para conectar Django a PostgreSQL mediante variables de entorno y servicio Gunicorn con Nginx.
- **Uso:** Configuración de `settings.py` para leer variables desde `.env` y archivo de servicio systemd.

#### 4. Pruebas Unitarias
- **Consulta:** Estructura de pruebas en Django TestCase para verificar creación de tutores, citas y fichas clínicas.
- **Uso:** Casos de prueba en `clinic/tests.py`.
