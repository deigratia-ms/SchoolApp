#!/usr/bin/env python
"""
Script to list all images in Cloudinary
"""

import os
import sys
from pathlib import Path
import django

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')

django.setup()

import cloudinary.api

print('=== IMAGES IN CLOUDINARY ===')
try:
    result = cloudinary.api.resources(type='upload', max_results=50)
    for resource in result.get('resources', []):
        public_id = resource['public_id']
        secure_url = resource['secure_url']
        print(f'{public_id} -> {secure_url}')
except Exception as e:
    print(f'Error: {e}')
