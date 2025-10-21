#!/bin/bash
# Download Spider dataset using command-line tools

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "Spider Dataset Download Helper"
echo "============================================================"
echo ""

# Check if spider.zip already exists
if [ -f "spider.zip" ]; then
    echo "✅ spider.zip already exists"
    echo "File size: $(du -h spider.zip | cut -f1)"
    echo ""
    echo "Run setup_spider.py to extract:"
    echo "  uv run python setup_spider.py"
    exit 0
fi

# Try downloading with wget or curl
echo "Downloading Spider dataset..."
echo "This may take several minutes (file size: ~95MB)"
echo ""

# Google Drive link (may require manual download)
GDRIVE_ID="1TqleXec_OykOYFREKKtschzY29dUcVAQ"
GDRIVE_URL="https://drive.google.com/uc?export=download&id=${GDRIVE_ID}"

# Alternative: Try with gdown if available
if command -v gdown &> /dev/null; then
    echo "Using gdown for Google Drive download..."
    gdown "$GDRIVE_ID" -O spider.zip
elif command -v wget &> /dev/null; then
    echo "Using wget..."
    wget --no-check-certificate "$GDRIVE_URL" -O spider.zip
elif command -v curl &> /dev/null; then
    echo "Using curl..."
    curl -L "$GDRIVE_URL" -o spider.zip
else
    echo "❌ Error: No download tool found (wget, curl, or gdown)"
    echo ""
    echo "Please install one of:"
    echo "  - wget: sudo apt install wget"
    echo "  - curl: sudo apt install curl"
    echo "  - gdown: pip install gdown"
    echo ""
    echo "Or download manually:"
    echo "  https://yale-lily.github.io/spider"
    exit 1
fi

# Verify download
if [ -f "spider.zip" ]; then
    SIZE=$(du -h spider.zip | cut -f1)
    echo ""
    echo "✅ Download complete! File size: $SIZE"
    echo ""
    echo "Next step: Extract the dataset"
    echo "  uv run python setup_spider.py"
else
    echo ""
    echo "❌ Download failed!"
    echo ""
    echo "Please download manually:"
    echo "1. Visit: https://yale-lily.github.io/spider"
    echo "2. Download the dataset (spider.zip)"
    echo "3. Place it in: $SCRIPT_DIR"
    exit 1
fi
