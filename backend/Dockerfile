FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# supercronic: planificador de tareas para el contenedor "tareas" (D-09)
ARG TARGETARCH
ARG SUPERCRONIC_VERSION=v0.2.33
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && arch="${TARGETARCH:-$(dpkg --print-architecture)}" \
    && curl -fsSL -o /usr/local/bin/supercronic \
       "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${arch}" \
    && chmod +x /usr/local/bin/supercronic \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
# Twofish es Python puro dentro del dominio (D-20): ya no se compila nada
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
