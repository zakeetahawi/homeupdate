#!/bin/bash
# ============================================================
# 🚀 start_production_service.sh
# نقطة دخول systemd لتشغيل نظام El-Khawaga ERP
# يُشغَّل بواسطة: run-production.service
#
# يُفوَّض التنفيذ إلى start-service.sh الذي يحتوي على المنطق الكامل
# ============================================================

exec /home/zakee/homeupdate/لينكس/start-service.sh
