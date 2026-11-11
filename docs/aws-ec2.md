# Despliegue de PetCare en AWS EC2

Esta guía deja el proyecto listo para usar PostgreSQL en AWS. No incorpora credenciales ni crea recursos de AWS: la instancia EC2, el dominio y los secretos deben pertenecer a la clínica.

## 1. Preparar PostgreSQL

En Ubuntu, instala PostgreSQL y crea una base y un usuario dedicados:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib python3-venv nginx
sudo -u postgres psql
```

En `psql`:

```sql
CREATE USER petcare_app WITH PASSWORD 'REEMPLAZAR_POR_UNA_CLAVE_ALEATORIA';
CREATE DATABASE petcare OWNER petcare_app;
\q
```

Para una base instalada en la misma EC2, deja PostgreSQL escuchando solo en `localhost`; no abras el puerto 5432 a Internet. Para una base independiente, limita el acceso a la aplicación mediante reglas de security group y una subred privada. En RDS, activa el certificado TLS de AWS y configura `DB_SSLMODE=verify-full` junto al certificado raíz correspondiente.

## 2. Configurar la aplicación

Clona o copia el proyecto en el servidor, crea un entorno virtual e instala dependencias:

```bash
cd /srv/petcare
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Crea `/etc/petcare.env` con permisos restringidos (`chmod 600`) y los siguientes valores:

```dotenv
DJANGO_SECRET_KEY=GENERAR_UNA_CLAVE_PRIVADA_ALEATORIA
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=petcare.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://petcare.example.com
DJANGO_SECURE_COOKIES=True
DJANGO_SECURE_SSL_REDIRECT=True
# Solo después de comprobar HTTPS en todos los subdominios:
DJANGO_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_HSTS_PRELOAD=True
DB_ENGINE=postgresql
DB_NAME=petcare
DB_USER=petcare_app
DB_PASSWORD=LA_CLAVE_DE_POSTGRESQL
DB_HOST=127.0.0.1
DB_PORT=5432
DB_SSLMODE=require
```

En producción, genera la clave con `python -c "import secrets; print(secrets.token_urlsafe(64))"`. No publiques el archivo de entorno ni lo agregues al repositorio. Reemplaza el dominio por el nombre DNS real y no uses la clave de ejemplo.

Ejecuta las migraciones, crea el primer administrador y reúne los archivos estáticos:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
```

No ejecutes el comando `seed_demo` en la base productiva.

Las opciones HSTS para subdominios y preload están desactivadas por defecto porque el dominio todavía no está definido. Puedes activarlas en `/etc/petcare.env` solo después de comprobar que **todos** los subdominios se sirven exclusivamente por HTTPS; la política se conserva en los navegadores durante mucho tiempo. Si esa condición no se cumple, deja ambas en `False`.

## 3. Ejecutar Gunicorn con systemd

Crea `/etc/systemd/system/petcare.service`, sustituyendo `petcare` por el usuario Linux que posee la aplicación:

```ini
[Unit]
Description=PetCare Django application
After=network.target postgresql.service

[Service]
User=petcare
Group=www-data
WorkingDirectory=/srv/petcare
EnvironmentFile=/etc/petcare.env
ExecStart=/srv/petcare/.venv/bin/gunicorn petcare.wsgi:application --workers 3 --bind 127.0.0.1:8000
Restart=on-failure
RestartSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now petcare
sudo systemctl status petcare
```

## 4. Publicar con Nginx y HTTPS

Configura Nginx para enviar `/` a `http://127.0.0.1:8000` y servir `/static/` desde `/srv/petcare/staticfiles/`. Envía `Host`, `X-Forwarded-For` y `X-Forwarded-Proto` al upstream. Habilita HTTPS con un certificado válido y permite en el security group únicamente el acceso necesario para SSH desde IP autorizadas, HTTP para la redirección y HTTPS para usuarios.

Al terminar, comprueba el inicio de sesión, el acceso a `/admin/`, la persistencia tras reiniciar Gunicorn y que las operaciones de agenda persistan en PostgreSQL. Revisa los logs con `journalctl -u petcare` y configura copias de seguridad periódicas de PostgreSQL.
