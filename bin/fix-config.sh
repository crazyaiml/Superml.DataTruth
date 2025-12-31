#!/bin/bash

# DataTruth - Quick Fix Script
# Fixes common configuration issues

echo "🔧 Fixing DataTruth Configuration Issues..."
echo ""

# Fix CORS_ORIGINS in .env
if [ -f .env ]; then
    if grep -q 'API_CORS_ORIGINS=\[' .env; then
        echo "Fixing API_CORS_ORIGINS format in .env..."
        sed -i.bak 's/API_CORS_ORIGINS=\[".*"\]/API_CORS_ORIGINS=*/' .env
        echo "✓ Fixed API_CORS_ORIGINS"
    fi
fi

echo ""
echo "✓ Configuration fixed!"
echo ""
echo "You can now run: ./start.sh"
