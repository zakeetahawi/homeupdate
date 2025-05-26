# 🏢 Elkhawaga Trading - Production Server

## 🌐 Live Website
- **Main Site:** https://elkhawaga.uk
- **CRM System:** https://crm.elkhawaga.uk
- **Admin Panel:** https://admin.elkhawaga.uk/admin/

## 🚀 Server Management

### Start Server
```bash
run-elkhawaga.bat
```

### Update System
```bash
# Manual update
update-system.bat

# Setup automatic daily updates (run as admin)
setup-auto-update.bat
```

## 📁 Important Files

### Production Files (DO NOT DELETE)
- `cloudflare-credentials.json` - Cloudflare authentication
- `cloudflared.yml` - Cloudflare tunnel configuration
- `run-elkhawaga.bat` - Main server startup script

### Update Files
- `update-system.bat` - Manual system update
- `auto-update-daily.bat` - Automatic daily update script
- `setup-auto-update.bat` - Setup automatic updates

### Logs
- `update-log.txt` - Update history and logs

## 🔄 Update Process

The update system:
1. ✅ Backs up production files
2. ✅ Pulls latest changes from repository
3. ✅ Restores production files
4. ✅ Updates dependencies
5. ✅ Runs database migrations
6. ✅ Collects static files

## ⚙️ Automatic Updates

- **Schedule:** Daily at 3:00 AM
- **Backup:** Production files are preserved
- **Logging:** All updates logged to `update-log.txt`
- **Safe:** No downtime during updates

## 🛠️ Troubleshooting

### If server won't start:
1. Check if Python is installed
2. Check if cloudflared.exe exists
3. Verify cloudflare-credentials.json exists

### If updates fail:
1. Check internet connection
2. Verify Git is installed
3. Check update-log.txt for errors

### Manual recovery:
```bash
# Reset to last working state
git stash
git reset --hard origin/main

# Restore production files from backup
copy *.backup original_name
```

## 📊 System Status

- **Repository:** https://github.com/zakeetahawi/homeupdate
- **Domain:** elkhawaga.uk
- **SSL:** Enabled via Cloudflare
- **Database:** PostgreSQL
- **Auto-Updates:** Enabled (if setup-auto-update.bat was run)

---

**🎉 This is a production server - Handle with care!**
