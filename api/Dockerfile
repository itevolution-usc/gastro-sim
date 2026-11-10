# ==============================================================
# GASTRO-SIM · Imagen de la API
# Responsable: Nestor Velasco (actividad 4612)
# ==============================================================
FROM python:3.12-slim

# Evita archivos .pyc y muestra los registros al instante.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Primero las dependencias: Docker reutiliza esta capa si no cambian.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY tests ./tests
COPY pytest.ini .

# Usuario sin privilegios: buena práctica de seguridad (RNF-07).
RUN useradd --create-home gastro
USER gastro

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
