# Imagen base liviana de Python
FROM python:3.11-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar e instalar dependencias primero (aprovecha el cache de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY app.py .

# Puerto que usa Streamlit por defecto
EXPOSE 8501

# Configuración para que Streamlit funcione bien en contenedor:
# - server.address 0.0.0.0 → acepta conexiones externas al contenedor
# - server.headless true   → no intenta abrir el navegador automáticamente
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
