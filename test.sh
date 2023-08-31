#!/bin/bash

rm -rf a
rm -rf b
rm -rf CODIBackup.log
rm -rf testBackup/*
./CODIBackup.py -bv
sleep 2
touch a
./CODIBackup.py -bv
sleep 2
touch b
./CODIBackup.py -bv
sleep 2
echo "asdf" >> a
./CODIBackup.py -bv
sleep 2
rm a
./CODIBackup.py -bv
