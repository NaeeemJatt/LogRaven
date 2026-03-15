# LogRaven — Production Dockerfile (with PyArmor obfuscation)
# Stage 1: Obfuscate source with PyArmor
FROM python:3.11-slim as builder

WORKDIR /src
RUN pip install pyarmor
COPY app/ /src/app/
RUN pyarmor gen --recursive -O /dist /src/app

# Stage 2: Runtime image with obfuscated code only
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libfontconfig1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy obfuscated app (no .py source files)
COPY --from=builder /dist /app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
