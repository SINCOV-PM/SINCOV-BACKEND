# SINCOV – Backend

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
│   ├── api/
│   │   ├── routes_predict.py
│   │   ├── routes_reports.py
│   │   └── routes_stations.py
│   ├── schemas/
│   │   └── predict_schema.py
│   ├── services/
│   │   ├── predict_service.py
│   │   ├── reports_service.py
│   │   └── stations_service.py
│   └── main.py
├── tests/
│   └── test_api.py
├── .gitignore
├── Dockerfile
├── LICENSE
├── README.md
├── requirements-freeze.txt
└── requirements.txt
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

## 🚀 Ejecución local

```bash
# Clonar repositorio
git clone https://github.com/SICOV-PM/SINCOV-BACKEND.git
cd SINCOV-BACKEND

# Instalar dependencias
pip install -r requirements.txt



🐳 Ejecutar con Docker

# Construir imagen
docker build -t sincov-backend .

# Correr contenedor
docker run --rm -p 8000:8000 sincov-backend
