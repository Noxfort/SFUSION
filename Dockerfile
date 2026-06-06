# Dockerfile para "Build & Extract"
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# 1. Instala ferramentas de compilação E a biblioteca problemática (libxcb-cursor0)
RUN apt-get update && apt-get install -y --no-install-recommends \
    patchelf \
    binutils \
    libqt6gui6 \
    libqt6widgets6 \
    libqt6dbus6 \
    libxkbcommon-x11-0 \
    libgl1 \
    libxcb-cursor0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Instala dependências Python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir pyinstaller

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copia o código fonte
COPY . .

# 4. Compila o executável usando o arquivo .spec
RUN pyinstaller --clean -y sfusion.spec