# 🚀 FOOLPROOF Fly.io Deployment Guide for Deigratia School Management System

**100% Copy-Paste Commands - No Confusion!**

This guide contains EXACT commands to copy and paste. Follow step by step without skipping anything.

---

## ✅ STEP 1: Install Fly CLI and Login

**Copy and paste these commands one by one:**

```powershell
# Install Fly CLI
iwr https://fly.io/install.ps1 -useb | iex
```

**After installation, close PowerShell completely and reopen it, then:**

```powershell
# Login to Fly.io (this will open your browser)
fly auth login
```

---

## ✅ STEP 2: Create Your App

**Copy and paste this EXACT command:**

```powershell
# Create app with PostgreSQL database
fly launch --name deigratia-school --region iad --no-deploy
```

**When prompted:**
- ❓ "Would you like to copy its configuration to the new app?" → Type: **No**
- ❓ "Do you want to tweak these settings before proceeding?" → Type: **No**
- ❓ "Overwrite Dockerfile?" → Type: **No**
- ❓ "Set secrets on deigratia-school?" → Type: **No**

**✅ This will create:**
- App name: `deigratia-school`
- Database: `deigratia-school-db`
- URL: `https://deigratia-school.fly.dev`

---

## ✅ STEP 3: Set Environment Variables

**Copy and paste this EXACT command:**

```powershell
# Import all environment variables from .env file
Get-Content .env | fly secrets import
```

---

## ✅ STEP 4: Deploy Your Application

**Copy and paste this EXACT command:**

```powershell
# Deploy to Fly.io
fly deploy
```

**⏱️ This will take 3-5 minutes. Wait for it to complete.**

---

## ✅ STEP 5: Setup Production Environment

**Copy and paste these commands one by one:**

```powershell
# Connect to your app
fly ssh console
```

**Inside the remote shell, copy and paste:**

```bash
# Run automated production setup
python manage.py setup_production

# Create admin user
python manage.py createsuperuser

# Exit remote shell
exit
```

---

## ✅ STEP 6: Verify Deployment

**Copy and paste these commands to test:**

```powershell
# Check app status
fly status

# View your website
fly open

# Check health endpoint
curl https://deigratia-school.fly.dev/health/
```

**✅ Your app is now live at: `https://deigratia-school.fly.dev`**

---

## 🌐 OPTIONAL: Connect Your Custom Domain

**Only do this AFTER successful deployment above.**

### Add Domain to Fly.io
```powershell
# Add your custom domain
fly certs add deigratiams.edu.gh
```

**Fly will show DNS records. Add these to your domain provider:**

- **A Record:**
  - Type: `A`
  - Name: `@`
  - Value: `[IP shown by Fly]`

- **CNAME Record:**
  - Type: `CNAME`
  - Name: `www`
  - Value: `deigratia-school.fly.dev.`

### Check certificate status:
```powershell
fly certs check deigratiams.edu.gh
```

**✅ Once verified, your app will be available at: `https://deigratiams.edu.gh`**

---

## 🔧 TROUBLESHOOTING (If Something Goes Wrong)

### View Logs
```powershell
# See what's happening
fly logs
```

### Restart App
```powershell
# Restart if needed
fly machine restart
```

### Check Status
```powershell
# Check app health
fly status
```

### Redeploy
```powershell
# If you need to redeploy
fly deploy
```

---

## 📋 USEFUL COMMANDS REFERENCE

| Command | What It Does |
|---------|-------------|
| `fly status` | Check if app is running |
| `fly logs` | View app logs |
| `fly open` | Open app in browser |
| `fly ssh console` | Connect to app terminal |
| `fly deploy` | Deploy changes |
| `fly secrets list` | View environment variables |

---

## � SUCCESS CHECKLIST

After deployment, verify these work:

- ✅ **Homepage loads:** `https://deigratia-school.fly.dev`
- ✅ **Health check works:** `https://deigratia-school.fly.dev/health/`
- ✅ **Admin login works:** `https://deigratia-school.fly.dev/my-admin/`
- ✅ **Static files load** (CSS, images, etc.)
- ✅ **Database works** (can create users, etc.)

---

## � IMPORTANT NOTES

1. **App Name:** `deigratia-school` (not school-management-system)
2. **URL:** `https://deigratia-school.fly.dev`
3. **Database:** Automatically created and connected
4. **All commands must be run from your project folder**
5. **Wait for each command to complete before running the next**

---

**🎯 THAT'S IT! Your school management system is now live on Fly.io!**
