# SINCOV – Backend
[![CI](https://github.com/SICOV-PM/SINCOV-BACKEND/actions/workflows/ci.yml/badge.svg)](https://github.com/SICOV-PM/SINCOV-BACKEND/actions/workflows/ci.yml)

API backend para consultar **estaciones**, **reportes** y **predicciones** de calidad del aire (p. ej., PM2.5).  
Está construido con **Python** y **FastAPI** (arquitectura por capas: `api` → `services` → `schemas`), con pruebas en `pytest` y soporte listo para **Docker**.

---

## 🚧 Estado
Estable para desarrollo local. Revisa la licencia en `LICENSE`.

---

## 🗂️ Estructura del proyecto
```bash
SINCOV-BACKEND/
├── app/
│   ├── api/              # Endpoints HTTP
│   ├── core/             # Configuración general
│   ├── data/             # Datos iniciales (stations.json)
│   ├── db/               # Conexión, modelos base y seeders
│   ├── models/           # ORM Models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Lógica de negocio
│   └── main.py           # Punto de entrada de la app FastAPI
├── alembic/              # Migraciones
├── tests/                # Pruebas Pytest
├── .github/workflows/    # CI/CD pipeline
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── README.md

```

## ⚙️ Servicios Disponibles


- **`app/main.py`**: punto de entrada; define la app FastAPI y monta las rutas.
- **`app/api/*`**: controladores (endpoints HTTP).
- **`app/services/*`**: lógica de negocio / acceso a datos.
- **`app/schemas/*`**: modelos para comparacion y prediccion
- **`tests/`**: pruebas `pytest`.

## ⚙️ Requisitos

- Python **3.10+**
- `pip`
- (Opcional) Docker

---

## 🔧 Variables de entorno

```bash
# Crea un archivo `.env` en la raíz del proyecto, basado en `.env.example`:
DATABASE_URL=postgresql+psycopg2://<username>:<password>@<host>:<port>/<database_name>
```

## 🚀 Ejecución local

```bash
# Clonar repositorio
git clone https://github.com/SICOV-PM/SINCOV-BACKEND.git
cd SINCOV-BACKEND

# Instalar dependencias
python -m venv venv
source venv/bin/activate    # en Linux/Mac
venv\Scripts\activate       # en Windows

pip install -r requirements.txt

# Levantar Postgres con Docker
docker-compose up --build

# Crear o actualizar estructura de BD
alembic upgrade head

```

##  🐳 Ejecutar con Docker

```bash
# Construir imagen
docker build -t sincov-backend .

# Correr contenedor
docker run --rm -p 8000:8000 sincov-backend

```

## 🧪 Pruebas

Ejecutar todas las pruebas locales:

```bash
pytest -v
```
