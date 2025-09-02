# Dockerfile لقسم التركيبات

# استخدام Python 3.11 كصورة أساسية
FROM python:3.11-slim

# تعيين متغيرات البيئة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=installations.settings

# تعيين مجلد العمل
WORKDIR /app

# تثبيت المتطلبات النظامية
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libmysqlclient-dev \
        pkg-config \
        libmagic1 \
        redis-tools \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملف المتطلبات
COPY requirements.txt /app/

# تثبيت متطلبات Python
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . /app/

# إنشاء مجلد الوسائط
RUN mkdir -p /app/media

# إنشاء مستخدم غير root
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# تعريض المنفذ
EXPOSE 8000

# تشغيل التطبيق
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "installations.wsgi:application"] 