# Favicon Setup

## Current Setup
The website is configured to use favicons in the following priority:

1. **Custom Favicon**: Upload a favicon through Django Admin → Site Settings → Favicon field
2. **School Logo**: If no favicon is uploaded, the school logo will be used
3. **Default Favicon**: Falls back to `favicon.ico` in this directory

## Recommended Favicon Sizes
- **16x16 pixels**: Standard favicon size
- **32x32 pixels**: High-resolution favicon
- **48x48 pixels**: Windows site icons
- **180x180 pixels**: Apple touch icon

## How to Add a Favicon

### Method 1: Through Django Admin (Recommended)
1. Go to Django Admin → Website → Site Settings
2. Upload your favicon image in the "Favicon" field
3. Save the settings

### Method 2: Replace Default Files
1. Create a `favicon.ico` file (16x16 or 32x32 pixels)
2. Place it in `static/website/images/favicon.ico`
3. Run `python manage.py collectstatic`

## File Formats Supported
- `.ico` (recommended for best browser compatibility)
- `.png` (modern browsers)
- `.svg` (scalable, modern browsers)
- `.jpg/.jpeg` (supported but not recommended)

## Tools for Creating Favicons
- **Online**: favicon.io, realfavicongenerator.net
- **Software**: GIMP, Photoshop, Canva
- **From Logo**: Use your existing school logo and resize it

## Current Fallback
A simple SVG favicon with the letter "D" (for Deigratia) is provided as a fallback.
