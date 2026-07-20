# Pet-Centric — Backend

Plataforma web para la gestión de mascotas perdidas y encontradas. API REST construida con **FastAPI** siguiendo arquitectura por capas.

## Stack Tecnológico

- **Python** 3.12+
- **FastAPI** — framework web
- **SQLAlchemy 2.x** (async) — ORM
- **PostgreSQL** — base de datos
- **Pydantic v2** — validación de datos
- **JWT** (python-jose) — autenticación
- **bcrypt / passlib** — hashing de contraseñas
- **Cloudinary** — almacenamiento de imágenes
- **Mailtrap** (aiosmtplib) — envío de correos (sandbox de pruebas)
- **Uvicorn** — servidor ASGI

## Base de Datos

- Llaves primarias: **UUID**.
- Soft delete obligatorio en todas las tablas relevantes (`deleted_at`, `is_active`), nunca se elimina un registro físicamente.
- Timestamps estándar: `created_at`, `updated_at`.
- Fechas en formato **ISO-8601 UTC** (`2026-07-03T18:45:20Z`).
- Enums se envían como strings (`"MALE"`, no `1`).

## Autenticación y Autorización

- **JWT** con Access Token de corta duración.
- **Refresh Token** persistido en BD (tabla `refresh_tokens`), con **rotación**: cada uso revoca el token anterior y emite uno nuevo, permitiendo detectar reuso indebido.
- Tokens de verificación de correo y reset de contraseña: **opacos** (no JWT), generados aleatoriamente y guardados como hash SHA-256 en BD, de un solo uso y con expiración.
- **RBAC**: roles y permisos, un usuario puede tener múltiples roles y permisos adicionales directos.
- El usuario autenticado siempre se obtiene desde el JWT — nunca se confía en `user_id` enviado por el cliente.
- Header de autenticación: `Authorization: Bearer <token>`.

## Instalación

```bash
# Clonar el repositorio
git clone <url-del-repo>
cd Backend_

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
.venv\Scripts\activate         # Windows

# Instalar dependencias
pip install -r requirements.txt
```

## Ejecutar el proyecto

```bash
uvicorn app.main:app --reload
```

La documentación interactiva queda disponible en:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Seguridad

- Contraseñas nunca se almacenan en texto plano (bcrypt).
- Nunca se devuelven en las respuestas: `password_hash`, `deleted_at`, tokens internos, `secret_key`.
- Política de contraseña segura: mínimo 8 caracteres, mayúscula, minúscula, número y carácter especial.
- El correo no revela si existe o no en el sistema en flujos de `forgot-password` / `resend-verification` (previene enumeración de usuarios).

## Roadmap

- [x] Autenticación completa (registro, verificación, login, refresh, logout, reset de contraseña)
- [x] Perfil de usuario
- [x] RBAC — dependencia
- [x] Gestión de mascotas
- [x] Reportes de mascotas perdidas/encontradas
- [] Notificaciones
- [] Mensajería
- [x] Panel de administración
