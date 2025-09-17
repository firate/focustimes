#!/bin/bash
set -e

# Cleanup
rm -rf build dist venv focustimes.icns

# Icon creation
echo "Icons are creating..."
if command -v rsvg-convert &> /dev/null; then
    mkdir -p focustimes.iconset
    rsvg-convert -w 16 -h 16 icon.svg > focustimes.iconset/icon_16x16.png
    rsvg-convert -w 32 -h 32 icon.svg > focustimes.iconset/icon_16x16@2x.png
    rsvg-convert -w 32 -h 32 icon.svg > focustimes.iconset/icon_32x32.png
    rsvg-convert -w 64 -h 64 icon.svg > focustimes.iconset/icon_32x32@2x.png
    rsvg-convert -w 128 -h 128 icon.svg > focustimes.iconset/icon_128x128.png
    rsvg-convert -w 256 -h 256 icon.svg > focustimes.iconset/icon_256x256@2x.png
    rsvg-convert -w 256 -h 256 icon.svg > focustimes.iconset/icon_256x256.png
    rsvg-convert -w 512 -h 512 icon.svg > focustimes.iconset/icon_256x256@2x.png
    rsvg-convert -w 512 -h 512 icon.svg > focustimes.iconset/icon_512x512.png
    rsvg-convert -w 1024 -h 1024 icon.svg > focustimes.iconset/icon_512x512@2x.png
    iconutil -c icns focustimes.iconset
    rm -rf focustimes.iconset
    echo "Done: focustimes.icns"
else
    echo "rsvg-convert not found! Install with Homebrew: brew install librsvg"
    exit 1
fi

# venv
python3 -m venv venv
source venv/bin/activate

# packages
pip install --upgrade pip setuptools wheel
pip install rumps pyinstaller

# build
pyinstaller focustimes.spec

# dmg staging
mkdir -p dist/dmg
cp -R dist/focustimes.app dist/dmg/
ln -s /Applications dist/dmg/Applications || true

# dmg build
hdiutil create -volname "focustimes" \
  -srcfolder "dist/dmg" \
  -ov -format UDZO "dist/focustimes.dmg"

echo "Ready: dist/focustimes.app ve dist/focustimes.dmg"