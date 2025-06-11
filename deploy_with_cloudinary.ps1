# PowerShell deployment script to fix Cloudinary media issues on Fly.io
# This script sets up Cloudinary environment variables and deploys the app

Write-Host "🚀 Deploying Deigratia School with Cloudinary fixes..." -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# Check if flyctl is installed
try {
    flyctl version | Out-Null
    Write-Host "✅ flyctl is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ flyctl is not installed. Installing now..." -ForegroundColor Red
    Write-Host "Installing flyctl..." -ForegroundColor Yellow
    iwr https://fly.io/install.ps1 -useb | iex
    
    # Add to PATH for current session
    $env:PATH += ";$env:USERPROFILE\.fly\bin"
    
    # Verify installation
    try {
        flyctl version | Out-Null
        Write-Host "✅ flyctl installed successfully" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to install flyctl. Please install manually." -ForegroundColor Red
        exit 1
    }
}

# Check if we're in the right directory
if (-not (Test-Path "fly.toml")) {
    Write-Host "❌ fly.toml not found. Please run this script from your project root." -ForegroundColor Red
    exit 1
}

Write-Host "📋 Setting up Cloudinary environment variables..." -ForegroundColor Yellow

# Set Cloudinary environment variables on Fly.io
# These are the credentials from your screenshot
try {
    flyctl secrets set `
        CLOUDINARY_CLOUD_NAME="deiduds9c" `
        CLOUDINARY_API_KEY="848364648584687" `
        CLOUDINARY_API_SECRET="Dmc79Lx5xo6T84CwfT2cGRWg" `
        DEBUG="False" `
        ENVIRONMENT="production"
    
    Write-Host "✅ Environment variables set successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to set environment variables: $_" -ForegroundColor Red
    exit 1
}

Write-Host "📦 Deploying application..." -ForegroundColor Yellow

# Deploy the application
try {
    flyctl deploy
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🎉 Your app should now have working media files!" -ForegroundColor Green
    Write-Host "🔗 Visit: https://deigratia-school.fly.dev/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📝 What was fixed:" -ForegroundColor Yellow
    Write-Host "   ✅ Added Cloudinary packages to requirements_production.txt" -ForegroundColor Green
    Write-Host "   ✅ Set Cloudinary environment variables on Fly.io" -ForegroundColor Green
    Write-Host "   ✅ Configured DEBUG=False for production" -ForegroundColor Green
    Write-Host ""
    Write-Host "🔍 To verify the fix:" -ForegroundColor Yellow
    Write-Host "   1. Visit your website" -ForegroundColor White
    Write-Host "   2. Try uploading an image in the admin panel" -ForegroundColor White
    Write-Host "   3. Check if existing images load properly" -ForegroundColor White
} catch {
    Write-Host "❌ Deployment failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📊 Checking app status..." -ForegroundColor Yellow
flyctl status

Write-Host ""
Write-Host "📋 Recent logs:" -ForegroundColor Yellow
flyctl logs --limit 20
