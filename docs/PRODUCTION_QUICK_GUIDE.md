# 🚀 Production Server Setup - Quick Guide

## System Overview

**Al-Khawaga CRM System** - Django-based enterprise management system

### Tech Stack:
- Django 5.2+
- PostgreSQL 14+
- Redis/Valkey
- Celery (Worker + Beat)
- Gunicorn (WSGI Server)
- WhiteNoise (Static files)
- Cloudflare Tunnel (Optional)

---

## 🎯 Two Deployment Options

### Option 1: Local Network Only (No Tunnel) ⚡

**Best for:** Internal use, better performance

```bash
./لينكس/run-production-no-tunnel.sh
```

**Access URLs:**
- Local: `http://localhost:8000`
- LAN: `http://192.168.1.30:8000`

**Pros:**
- ⚡ High performance
- 🔒 More secure (no internet exposure)
- 💪 More stable (no internet dependency)
- 🎯 Simple configuration

**Cons:**
- ❌ No internet access
- ❌ No HTTPS
- ❌ Requires VPN for remote access

---

### Option 2: Internet Access (With Tunnel) 🌐

**Best for:** Remote teams, external clients

```bash
./لينكس/run-production.sh
```

**Access URLs:**
- Internet: `https://elkhawaga.uk`
- Local: `http://localhost:8000`

**Pros:**
- 🌐 Access from anywhere
- 🔒 HTTPS encryption
- 🛡️ DDoS protection
- ✅ Professional domain

**Cons:**
- 🐌 Slightly slower
- 📡 Requires stable internet
- 🔧 More complex setup

---

## 🔐 Default Credentials

```
Username: admin
Password: admin123
```

⚠️ **Change immediately after first login!**

---

## 📊 Active Services

When running, the system starts:

- ✅ **Gunicorn** (Web server) - Port 8000
- ✅ **Celery Worker** (Background tasks)
- ✅ **Celery Beat** (Scheduled tasks)
- ✅ **Redis/Valkey** (Cache & queues)
- ✅ **Auto Backup** (Every hour)

---

## 🔍 Monitoring

### View Logs:

```bash
# Celery Worker
tail -f logs/celery_worker.log

# Celery Beat
tail -f logs/celery_beat.log

# Backups
tail -f logs/db_backup.log

# Django
tail -f logs/django.log

# Errors
tail -f logs/errors.log
```

### Check Status:

```bash
# All services
ps aux | grep -E 'gunicorn|celery|redis'

# Database
python manage.py monitor_db --once

# Redis
redis-cli ping
```

---

## 🛑 Stop System

Press `Ctrl+C` in the terminal where the system is running.

All services will stop automatically.

---

## 🔄 Restart System

```bash
# Stop (Ctrl+C)
# Then start again
./لينكس/run-production-no-tunnel.sh
```

---

## 🌐 Access from Other Devices

### From Computer:
```
http://192.168.1.30:8000
```

### From Mobile:
1. Connect to same WiFi
2. Open browser
3. Go to: `http://192.168.1.30:8000`

---

## 🔧 Troubleshooting

### Can't access from another device:

```bash
# Check firewall
sudo ufw allow 8000/tcp

# Check server IP
ip addr show | grep "inet "
```

### System is slow:

```bash
# Check resources
htop

# Check slow queries
tail -f logs/slow_queries.log
```

### Database error:

```bash
# Apply migrations
source venv/bin/activate
python manage.py migrate
```

---

## 📋 Quick Reference

### File Structure:
```
/home/zakee/homeupdate/
├── لينكس/
│   ├── run-production.sh              # With tunnel
│   └── run-production-no-tunnel.sh    # Without tunnel
├── logs/                               # All logs
├── media/backups/                      # Auto backups
└── venv/                               # Virtual environment
```

### Important Commands:

```bash
# Start (no tunnel)
./لينكس/run-production-no-tunnel.sh

# Start (with tunnel)
./لينكس/run-production.sh

# View logs
tail -f logs/celery_worker.log

# Database status
python manage.py monitor_db --once

# Manual backup
python manage.py dbbackup

# Clean old notifications
python manage.py cleanup_notifications
```

---

## 🎯 Recommendations

### Use **No Tunnel** if:
- ✅ Internal use only
- ✅ Performance is critical
- ✅ You have VPN for remote access
- ✅ Highly sensitive data

### Use **With Tunnel** if:
- ✅ Need internet access
- ✅ Remote team/clients
- ✅ Need HTTPS
- ✅ No VPN available

### Use **Both** for:
- 🎯 Best of both worlds
- ⚡ Fast local access
- 🌐 Secure remote access
- 💪 Maximum flexibility

---

## 📚 Full Documentation

- [Complete Deployment Guide (Arabic)](./دليل_تشغيل_الإنتاج.md)
- [Deployment Comparison (Arabic)](./مقارنة_طرق_التشغيل.md)
- [Quick Start (Arabic)](./README_تشغيل_بدون_تانل.md)

---

## 🆘 Support

For issues:
1. Check logs in `/home/zakee/homeupdate/logs/`
2. Review documentation files
3. Check systemd logs: `journalctl -u run-production.service`

---

**Last Updated:** December 2025  
**Version:** 2.0
