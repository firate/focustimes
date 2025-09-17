#!/bin/bash
set -e

# Cleanup
rm -rf build dist venv

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