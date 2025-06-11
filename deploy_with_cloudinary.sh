#!/bin/bash

# Deployment script to fix Cloudinary media issues on Fly.io
# This script sets up Cloudinary environment variables and deploys the app

echo "🚀 Deploying Deigratia School with Cloudinary fixes..."
echo "=================================================="

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "❌ flyctl is not installed. Please install it first:"
    echo "   Windows: iwr https://fly.io/install.ps1 -useb | iex"
    echo "   macOS/Linux: curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "fly.toml" ]; then
    echo "❌ fly.toml not found. Please run this script from your project root."
    exit 1
fi

echo "📋 Setting up Cloudinary environment variables..."

# Set Cloudinary environment variables on Fly.io
# These are the credentials from your screenshot
flyctl secrets set \
    CLOUDINARY_CLOUD_NAME="deiduds9c" \
    CLOUDINARY_API_KEY="848364648584687" \
    CLOUDINARY_API_SECRET="Dmc79Lx5xo6T84CwfT2cGRWg" \
    DEBUG="False" \
    ENVIRONMENT="production"

if [ $? -eq 0 ]; then
    echo "✅ Environment variables set successfully"
else
    echo "❌ Failed to set environment variables"
    exit 1
fi

echo "📦 Deploying application..."

# Deploy the application
flyctl deploy

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo ""
    echo "🎉 Your app should now have working media files!"
    echo "🔗 Visit: https://deigratia-school.fly.dev/"
    echo ""
    echo "📝 What was fixed:"
    echo "   ✅ Added Cloudinary packages to requirements_production.txt"
    echo "   ✅ Set Cloudinary environment variables on Fly.io"
    echo "   ✅ Configured DEBUG=False for production"
    echo ""
    echo "🔍 To verify the fix:"
    echo "   1. Visit your website"
    echo "   2. Try uploading an image in the admin panel"
    echo "   3. Check if existing images load properly"
else
    echo "❌ Deployment failed"
    exit 1
fi

echo ""
echo "📊 Checking app status..."
flyctl status

echo ""
echo "📋 Recent logs:"
flyctl logs --limit 20
