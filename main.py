#!/usr/bin/env python3

import json
import hashlib
import os
from datetime import datetime, timezone, timedelta
import shutil
from argparse import ArgumentParser


def peek(timestring):
	global backups
	timestamp = datetime.strptime(timestring, "%Y-%m-%dT%H:%M:%S")
	relevant = False
	folderStructure = {"files": {}, "folders": {}}
	for backup in backups:
		if not relevant:
			created = backup["created"]
			ts = datetime.strptime(created, "%Y-%m-%dT%H:%M:%S")
			if ts <= timestamp:
				relevant = True
		if relevant:
			for file in backup["files"].keys():
				if file not in folderStructure["files"].keys():
					if backup["files"][file] != "":
						folderStructure["files"][file] = "/" + backup["created"] + file
					else:
						folderStructure["files"][file] = ""
			for folder in backup["folders"].keys():
				if folder not in folderStructure["folders"].keys():
					if backup["folders"][folder]:
						folderStructure["folders"][folder] = folder
	return folderStructure


def recover(timestring, dst=""):
	if len(dst) >= 1:
		if dst[-1] == "/":
			dst = dst[:-1]
	folderStructure = peek(timestring)
	for file in folderStructure["files"].keys():
		if file != "":
			cp(destination + folderStructure["files"][file], dst + file)
	for folder in folderStructure["folders"].keys():
		if not os.path.isdir(dst + folder):
			os.makedirs(dst + folder)


def cp(src, dst):
	dirname = os.path.dirname(dst)
	if not os.path.isdir(dirname):
		os.makedirs(dirname)
	shutil.copyfile(src, dst)


def mv(src, dst):
	dirname = os.path.dirname(dst)
	if not os.path.isdir(dirname):
		os.makedirs(dirname)
	shutil.move(src, dst)


config = None
with open("config.json", "r") as f:
	config = json.load(f)

destination = config["destination"]
if destination[-1] != "/":
	destination += "/"
if not os.path.isdir(destination):
	os.makedirs(destination)

backupTimes = []
backups = []
for f in os.listdir(destination):
	if os.path.isdir(destination + f):
		backupTimes.append(f)
backupTimes.sort(reverse=True)
for b in backupTimes:
	b = destination + b + ".json"
	with open(b, "r") as f:
		backup = json.load(f)
		backup["state"] = "uptodate"
		backups.append(backup)


def backup():
	global backups
	global destination
	timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
	currentBackupFolder = destination + timestamp + "/"
	currentBackupConfigLocation = destination + timestamp + ".json"
	backupType = "d"
	if len(backups) == 0:
		backupType = "b"
	currentBackup = {"files": {}, "folders": {}, "created": timestamp, "edited": timestamp, "type": backupType}
	os.makedirs(currentBackupFolder)

	for src in config["folders"]:
		backupFolder(src, currentBackup)

	folderStructure = {"files": {}, "folders": {}}
	for backup in backups:
		for file in backup["files"].keys():
			if file not in folderStructure["files"].keys():
				folderStructure["files"][file] = backup["files"][file]
		for folder in backup["folders"].keys():
			if folder not in folderStructure["folders"].keys():
				folderStructure["folders"][folder] = backup["folders"][folder]
	for file in folderStructure["files"].keys():
		if not os.path.isfile(file):
			currentBackup["files"][file] = ""
	for folder in folderStructure["folders"].keys():
		if not os.path.isdir(folder):
			currentBackup["folders"][folder] = False

	with open(currentBackupConfigLocation, "w") as f:
		json.dump(currentBackup, f, indent=4)

	backupDays = config["days"]
	for backup in backups:
		backupType = backup["type"]
		if backupType == "d":
			created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
			if datetime.now() > created + timedelta(days=backupDays * 1):
				backup["type"] = "w"
				backup["state"] = "changed"
		else:
			break
	for i in reversed(range(len(backups))):
		backup = backups[i]
		backupType = backup["type"]
		if backupType == "w":
			while True:
				if i > 0:
					b = backups[i - 1]
					if b["type"] == backupType:
						created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
						edited = datetime.strptime(b["edited"], "%Y-%m-%dT%H:%M:%S")
						if edited < created + timedelta(days=7):
							mergeInto(b, backup)
							del backups[i - 1]
							i -= 1
						else:
							break
					else:
						break
				else:
					break
		elif backupType == "d":
			break

	backupWeeks = config["weeks"]
	for backup in backups:
		backupType = backup["type"]
		if backupType == "w":
			created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
			if datetime.now() > created + timedelta(days=backupDays * 1 + backupWeeks * 7):
				backup["type"] = "m"
				backup["state"] = "changed"
		else:
			break
	for i in reversed(range(len(backups))):
		backup = backups[i]
		backupType = backup["type"]
		if backupType == "m":
			while True:
				if i > 0:
					b = backups[i - 1]
					if b["type"] == backupType:
						created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
						edited = datetime.strptime(b["edited"], "%Y-%m-%dT%H:%M:%S")
						if edited < created + timedelta(days=28):
							mergeInto(b, backup)
							del backups[i - 1]
							i -= 1
						else:
							break
					else:
						break
				else:
					break
		elif backupType == "w":
			break

	backupMonths = config["months"]
	for backup in backups:
		backupType = backup["type"]
		if backupType == "m":
			created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
			if datetime.now() > created + timedelta(days=backupDays * 1 + backupWeeks * 7 + backupMonths * 28):
				backup["type"] = "y"
				backup["state"] = "changed"
		else:
			break
	for i in reversed(range(len(backups))):
		backup = backups[i]
		backupType = backup["type"]
		if backupType == "y":
			while True:
				if i > 0:
					b = backups[i - 1]
					if b["type"] == backupType:
						created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
						edited = datetime.strptime(b["edited"], "%Y-%m-%dT%H:%M:%S")
						if edited < created + timedelta(days=28 * 12):
							mergeInto(b, backup)
							del backups[i - 1]
							i -= 1
						else:
							break
					else:
						break
				else:
					break
		elif backupType == "m":
			break

	backupYears = config["years"]
	for backup in backups:
		backupType = backup["type"]
		if backupType == "y":
			created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
			if datetime.now() > created + timedelta(days=backupDays * 1 + backupWeeks * 7 + backupMonths * 28 + backupYears * 12 * 28):
				backup["type"] = "b"
				backup["state"] = "changed"
		else:
			break
	for i in reversed(range(len(backups))):
		backup = backups[i]
		backupType = backup["type"]
		if backupType == "b":
			while True:
				if i > 0:
					b = backups[i - 1]
					if b["type"] == backupType:
						created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
						edited = datetime.strptime(b["edited"], "%Y-%m-%dT%H:%M:%S")
						mergeInto(b, backup)
						del backups[i - 1]
						i -= 1
					else:
						break
				else:
					break
		elif backupType == "y":
			break
	for backup in backups:
		if backup["state"] == "changed":
			with open(destination + backup["created"] + ".json", "w") as f:
				json.dump(backup, f, indent=4)


def mergeInto(update, base):
	base["edited"] = update["edited"]
	for file in update["files"]:
		if update["files"][file] == "":
			if base["type"] == "b":
				if file in base["files"].keys():
					del base["files"][file]
					base["state"] = "changed"
			else:
				base["files"][file] = update["files"][file]
				base["state"] = "changed"
			if os.path.isfile(destination + base["created"] + file):
				os.remove(destination + base["created"] + file)
				while True:
					file = os.path.dirname(file)
					if file == "/":
						break
					if len(os.path.listdir(file)) == 0:
						os.rmdir(destination + base["created"] + file)
					else:
						break
		else:
			base["files"][file] = update["files"][file]
			mv(destination + update["created"] + file, destination + base["created"] + file)
			base["state"] = "changed"
	for folder in update["folders"].keys():
		exists = update["folders"][folder]
		if base["type"] == "b" and not exists:
			if folder in base["folders"].keys():
				del base["folders"][folder]
				base["state"] = "changed"
		else:
			base["folders"][folder] = exists
	os.remove(destination + update["created"] + ".json")
	shutil.rmtree(destination + update["created"] + "/")


def backupFolder(src, currentBackup):
	global backups
	if os.path.isdir(src):
		if src[-1] != "/":
			src += "/"
		filename = src[:-1]
		filename = filename[filename.rfind("/") + 1:]
		filename += "/"
		for ignored in config["ignore"]:
			if filename == ignored:
				return
		for f in os.listdir(src):
			backupFolder(src + f, currentBackup)
		src = src[:-1]
		while True:
			folderExists = -1
			for backup in backups:
				if src in backup["folders"].keys():
					if backup["folders"][src]:
						folderExists = 1
					else:
						folderExists = 0
					break
			if folderExists == -1 or folderExists == 0:
				currentBackup["folders"][src] = True
			src = os.path.dirname(src)
			if src == "/" or src == "" or folderExists == 1:
				break
	elif os.path.isfile(src):
		filename = filename[src.rfind("/") + 1:]
		for ignored in config["ignore"]:
			if filename == ignored:
				return
		storedHash = ""
		for backup in backups:
			if src in backup["files"].keys():
				storedHash = backup["files"][src]
				break
		calculatedHash = ""
		with open(src, "rb") as f:
			sha256 = hashlib.sha256()
			while True:
				data = f.read(4096)
				if not data:
					break
				sha256.update(data)
			calculatedHash = sha256.hexdigest()
		if calculatedHash != storedHash:
			currentBackup["files"][src] = calculatedHash
			cp(src, destination + currentBackup["created"] + src)


if __name__ == "__main__":
	PROJECTNAME = "CODIBackup"

	__version__ = "0.1.0"

	parser = ArgumentParser()
	parser.add_argument("-v", "--verbose", action="store_true", help="prints what is done")
	parser.add_argument("-b", "--backup", action="store_true", help="creates a backup")
	parser.add_argument("-p", "--peek", help="lists all files from a backup")
	parser.add_argument("-r", "--recover", help="recovers a specific state from the backups")
	args = parser.parse_args()

	if args.backup:
		backup()
	else:
		if args.peek is not None:
			folderStructure = peek(args.peek)
			for file in folderStructure["files"].keys():
				print(file)
		elif args.recover is not None:
			recover(args.recover)
