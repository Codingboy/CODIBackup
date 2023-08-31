#!/bin/bash

mkdir CODIBackup
cp -r codi CODIBackup
rm -rf CODIBackup/codi/__pycache__
cp CODIBackup.py CODIBackup
cp CODIBackup.sh CODIBackup
cp README.md CODIBackup
cp LICENSE CODIBackup
cp .config.json CODIBackup/config.json
zip -r CODIBackup.zip CODIBackup
rm -rf CODIBackup
