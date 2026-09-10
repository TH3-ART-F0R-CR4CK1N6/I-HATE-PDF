FROM python:3.11-slim

# Dependencias de sistema necesarias:
# - poppler-utils: convertir PDF a imágenes
# - ghostscript: compresión real de PDF
# - libreoffice: convertir Word -> PDF
# - qpdf: reparación/optimización de PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    ghostscript \
    qpdf \
    libreoffice \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/tmp

ENV PORT=10000
EXPOSE 10000

CMD ["gunicorn", "-w", "2", "-k", "gthread", "--threads", "4", "-b", "0.0.0.0:10000", "--timeout", "300", "app:app"]
