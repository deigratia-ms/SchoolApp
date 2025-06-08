# 🚀 Deploying Your Django Project to Fly.io (Windows + PowerShell)

This guide walks you step-by-step through deploying your Django 5.1.6 project to Fly.io, using Windows PowerShell. You are using Python 3.12.10, WhiteNoise for static files, and an external PostgreSQL database (for now). This guide also includes switching to Fly.io PostgreSQL later and connecting a custom domain for Deigratia Montessori School.

<!-- SEO: Ensure robots.txt, sitemap.xml, and meta tags are present for best ranking. -->

---

## ✅ 1. Create a Fly.io Account and Install CLI

### Create Account
Go to [https://fly.io](https://fly.io) and create a free account.

### Install Fly CLI (on PowerShell)
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

### Login to Fly.io
```powershell
fly auth login
```

---

## 🧰 2. Prepare Your Django Project

### .env settings (already done)
Ensure your `.env` contains keys like:
```
DEBUG=False
SECRET_KEY=...
ALLOWED_HOSTS=localhost,127.0.0.1,*.fly.dev,deigratiams.edu.gh
DATABASE_URL=...
ENVIRONMENT=production
DEFAULT_SCHOOL_NAME=Deigratia Montessori School
TIME_ZONE=Africa/Accra
...
```

### 🆕 Production Environment Template
A new template file `.env.production.template` is available with all recommended production settings. Copy and customize it for your deployment.

### Django settings (already correct)
You're using:
- `whitenoise.storage.CompressedManifestStaticFilesStorage`
- `STATIC_ROOT = BASE_DIR / 'staticfiles'`

These are correct for production.

---

## 🐳 3. Docker and Fly Configuration

### Dockerfile ✅
Already correct. It uses:
```dockerfile
CMD gunicorn ricas_school_manager.wsgi:application --bind 0.0.0.0:$PORT
```

### fly.toml ✅
The file contains correct app name, ports, and static file serving.

If not yet created, create with:
```powershell
fly launch --name school-management-system --region iad --no-deploy
```

---

## 🔐 4. Set Environment Variables on Fly.io

Upload your `.env` to Fly:
```powershell
fly secrets import < .env
```

---

## 🚀 5. Deploy to Fly.io

```powershell
fly deploy
```

Fly will show a deployed URL like:  
➡️ `https://school-management-system.fly.dev`

---

## 🛠 6. Run Migrations and Setup Production Environment

Open a remote shell into your Fly instance:
```powershell
fly ssh console
```

Then run inside the remote shell:
```bash
# Option 1: Manual setup (your current method)
python manage.py migrate
python manage.py collectstatic --noinput

# Option 2: Automated production setup (NEW - recommended)
python manage.py setup_production

# Create superuser
python manage.py createsuperuser
exit
```

### 🆕 What the new `setup_production` command does:

**Automated 6-Step Production Setup:**

1. **Database Migrations** - Creates all necessary database tables
2. **Cache Table Creation** - Sets up database caching for better performance
3. **Static Files Collection** - Gathers CSS/JS files for production serving
4. **Logging Directory** - Creates logs folder for application monitoring
5. **Database Verification** - Tests database connectivity
6. **Settings Validation** - Checks for security and configuration issues

**Key Benefits:**
- ✅ **Safe to run multiple times** - Won't break existing setup
- ✅ **Detailed progress tracking** - Shows 1/6, 2/6, etc.
- ✅ **Error handling** - Continues on non-critical errors
- ✅ **Success summary** - Clear feedback on what worked
- ✅ **Production validation** - Catches common deployment issues

**Command Options:**
```bash
# Full setup
python manage.py setup_production

# Skip specific steps
python manage.py setup_production --skip-cache --skip-static
```

---

## 🐘 7. (Optional) Switch to Fly.io PostgreSQL

You can switch later. When you're ready:

### Provision a new PostgreSQL database:
```powershell
fly postgres create --name school-db --region iad
```

Note the `DATABASE_URL` and update it in Fly secrets:

```powershell
fly secrets set DATABASE_URL=your_new_database_url_here
```
Open console:
```powershell
fly ssh console
```
Then run:
```bash
# Option 1: Manual setup
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

# Option 2: Automated setup (recommended)
python manage.py setup_production
python manage.py createsuperuser
exit
```


You can view your current secrets with:
```powershell
fly secrets list
```

Then SSH and migrate again if needed.

---

## 🌐 8. Connect Your Custom Domain (`deigratiams.edu.gh`)

### Add Domain to Fly.io
```powershell
fly certs add deigratiams.edu.gh
```

Fly will show DNS records. Example output:

- A Record for root domain:
    - Type: `A`
    - Name: `@`
    - Value: `76.76.21.21` (or IP shown by Fly)

- CNAME for `www`:
    - Type: `CNAME`
    - Name: `www`
    - Value: `school-management-system.fly.dev.`

### Update DNS on Ghana.com

1. Login to Ghana.com Domain Management Panel.
2. Go to DNS Management or Nameserver Settings.
3. Add the records above.
4. Save and wait ~15–60 minutes.

### Check certificate status:
```powershell
fly certs check deigratiams.edu.gh
```

Once verified, your app will be served on:
➡️ `https://deigratiams.edu.gh`

---

## ✅ Useful Commands

| Command | Description |
|--------|-------------|
| `fly deploy` | Deploy app |
| `fly logs` | View logs |
| `fly ssh console` | Access remote shell |
| `fly secrets set KEY=val` | Set new secret |
| `fly status` | Check app status |
| `python manage.py setup_production` | 🆕 Automated production setup |
| `python manage.py backup_system` | 🆕 Create system backup |
| `python manage.py restore_system backup.zip` | 🆕 Restore from backup |

## 🆕 Production Features Added

### Enhanced Security & Performance
- ✅ **Automatic HTTPS enforcement** in production
- ✅ **Enhanced logging** for better debugging
- ✅ **Database connection optimization**
- ✅ **Production settings validation**

### New Management Commands
- ✅ **`setup_production`** - Automated production environment setup
- ✅ **Enhanced backup system** - Already available in your project
- ✅ **Production health checks** - Available at `/health/`

### Documentation
- ✅ **`PRODUCTION_CHECKLIST.md`** - Complete deployment checklist
- ✅ **`.env.production.template`** - Production environment template

## 🔍 Troubleshooting

### Check Application Health
```powershell
# Check if app is running
fly status

# View application logs
fly logs

# Test health endpoint
curl https://school-management-system.fly.dev/health/
```

### Common Issues
```powershell
# If static files not loading
fly ssh console
python manage.py collectstatic --noinput --clear
exit

# If database issues
fly ssh console
python manage.py dbshell
exit
```

---

### 🧠 Tip: Run all Fly commands in PowerShell from your project root (where `manage.py` lives).
