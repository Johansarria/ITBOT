# Etapa 1: Usar una imagen base oficial de Python.
FROM python:3.12-slim

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Prevenir que Python escriba archivos .pyc
ENV PYTHONDONTWRITEBYTECODE 1

# Asegurar que la salida de Python se envíe directamente a la terminal (sin búfer)
ENV PYTHONUNBUFFERED 1

# Copiar el archivo de dependencias primero para aprovechar el cache de Docker
COPY requirements.txt .

# Instalar las dependencias
RUN apt-get update && apt-get install -y libgomp1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación al directorio de trabajo
COPY . .

# Copiar el directorio de análisis de datos explícitamente
COPY data/analisis /app/data/analisis

# El comando para ejecutar la aplicación se especificará en el archivo docker-compose.yml
# Esto permite que la misma imagen sea utilizada para diferentes servicios (ej. listener, worker).
