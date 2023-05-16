#!/bin/bash

rm -f ~/backup/*
rm -f CODIBackup.log
rm -f a b c
./CODIBackup.py -v -b
sleep 1
touch a
./CODIBackup.py -v -b
sleep 1
touch b
./CODIBackup.py -v -b
sleep 1
touch c
./CODIBackup.py -v -b
sleep 1
echo "bla" > a
./CODIBackup.py -v -b
sleep 1
rm -f a
./CODIBackup.py -v -b
