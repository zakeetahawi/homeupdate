# 🚀 Production Deployment Workflow

## 📋 **System Configuration**

### 🖥️ **This Machine (Production Server):**
- **Role:** Deployment-only server
- **Domain:** elkhawaga.uk
- **Function:** Receives updates, does NOT push changes
- **Status:** Live production environment

### 💻 **Development Machine:**
- **Role:** Development and updates
- **Function:** Makes changes and pushes to repository
- **Repository:** https://github.com/zakeetahawi/homeupdate

---

## 🔄 **Workflow Process**

### 📥 **Receiving Updates (This Machine):**

#### **Manual Update:**
```bash
update-system.bat
```

#### **Automatic Updates:**
```bash
# Setup once (run as administrator)
setup-auto-update.bat

# Runs daily at 3:00 AM automatically
```

### 📤 **Sending Updates (Development Machine):**
1. Make changes on development machine
2. Test changes locally
3. Push to GitHub repository
4. Production server will receive updates automatically

---

## 🛡️ **Protected Files**

These files are **NEVER** updated from repository:
- `cloudflare-credentials.json` - Cloudflare authentication
- `cloudflared.yml` - Tunnel configuration
- `run-elkhawaga.bat` - Production launcher
- `*.bat` files - Production scripts

---

## 🚀 **Production Commands**

### **Start Website:**
```bash
run-elkhawaga.bat
```

### **Check for Updates:**
```bash
update-system.bat
```

### **View Update Log:**
```bash
type update-log.txt
```

---

## 🌐 **Live URLs**

- **Main Site:** https://elkhawaga.uk
- **CRM System:** https://crm.elkhawaga.uk
- **Admin Panel:** https://admin.elkhawaga.uk/admin/
- **API Access:** https://api.elkhawaga.uk

---

## ⚠️ **Important Notes**

1. **DO NOT** make code changes on this machine
2. **DO NOT** push changes from this machine to GitHub
3. **DO** use update-system.bat to receive updates
4. **DO** keep production files (credentials, configs) safe
5. **DO** monitor update-log.txt for any issues

---

## 🆘 **Emergency Recovery**

If something goes wrong:
```bash
# Reset to last working state
git stash
git reset --hard origin/main

# Restore production files
copy *.backup original_name
```

---

**🎉 This machine is now a dedicated production server!**
