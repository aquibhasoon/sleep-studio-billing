FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Temporary key used only while collecting static files during the build.
RUN SECRET_KEY=build-only-placeholder python manage.py collectstatic --noinput

CMD exec gunicorn billing_system.wsgi:application 
    --bind 0.0.0.0:$PORT 
    --workers 2 
    --threads 4 
    --timeout 120