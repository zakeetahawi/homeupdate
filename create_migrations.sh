#!/bin/bash
cd /home/zakee/homeupdate
source venv/bin/activate
python manage.py makemigrations accounting orders
