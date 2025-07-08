#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Install or upgrade Gunicorn if needed
pip install --upgrade gunicorn

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start Gunicorn with our configuration
exec gunicorn -c gunicorn_config.py crm.wsgi:application 