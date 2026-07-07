# Pet-Centric — Backend

Plataforma web para la gestión de mascotas perdidas y encontradas. API REST construida con **FastAPI** siguiendo arquitectura por capas (API → Service → Repository → Model), pensada para escalar sin reescribir módulos.

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

## Arquitectura

app/
├── api/ # Endpoints REST organizados por módulo (recibe, valida, delega al service)
├── core/ # Configuración, seguridad, conexión a BD, excepciones globales
├── models/ # Modelos SQLAlchemy (tablas de la base de datos)
├── schemas/ # Modelos Pydantic (request/response), un DTO por operación
├── repositories/ # Acceso a datos (CRUD puro, sin lógica de negocio, sin commit)
├── services/ # Lógica de negocio, coordina repositories y transacciones
├── dependencies/ # Dependencias reutilizables de FastAPI (ej. auth JWT)
├── middlewares/ # Middlewares globales (CORS, logging, etc.)
└── utils/ # Helpers reutilizables (mailer, validadores, respuesta estándar)

**Reglas de la arquitectura:**

- Los endpoints **nunca** contienen lógica de negocio: solo reciben, validan y delegan al Service.
- Toda la lógica de negocio vive en el Service.
- Toda interacción con la base de datos vive en el Repository.
- Los repositories hacen `flush()`, no `commit()` — la transacción la controla el Service.
- Cada operación tiene su propio DTO (schema); nunca se reutilizan entre endpoints.

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

## Variables de Entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
# App
APP_NAME=Pet-Centric
APP_ENV=development

# Base de datos
DATABASE_URL=postgresql+asyncpg://usuario:password@localhost:5432/petcentric

# JWT
SECRET_KEY=tu_clave_secreta_super_segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
EMAIL_VERIFICATION_EXPIRE_MINUTES=1440
PASSWORD_RESET_EXPIRE_MINUTES=30
RESEND_VERIFICATION_COOLDOWN_SECONDS=60

# Cloudinary
CLOUDINARY_CLOUD_NAME=tu_cloud_name
CLOUDINARY_API_KEY=tu_api_key
CLOUDINARY_API_SECRET=tu_api_secret

# Mailtrap
MAILTRAP_HOST=sandbox.smtp.mailtrap.io
MAILTRAP_PORT=2525
MAILTRAP_USERNAME=tu_usuario
MAILTRAP_PASSWORD=tu_password
MAILTRAP_SENDER_EMAIL=noreply@pet-centric.com
MAILTRAP_SENDER_NAME=Pet-Centric

# Frontend
FRONTEND_URL=http://localhost:4200
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
- [x] Perfil de usuario (`user_profiles`)
- [ ] RBAC — dependencia `require_permission`
- [x] Gestión de mascotas
- [ ] Reportes de mascotas perdidas/encontradas
- [ ] Notificaciones
- [ ] Mensajería
- [ ] Panel de administración
