#!/usr/bin/env python3

import json
import hashlib
import os
from datetime import datetime, timezone, timedelta
import shutil
from argparse import ArgumentParser
from codi.codiio import Path, File
from codi.codiar import Archive

#TODO hour backups
#TODO check if edited before checking hash


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

destination = Path(config["destination"], True)
if not destination.isdir():
	destination.mkdir()

backupTimes = []
backups = []
for f in destination.listdir():
	if f.isfile():
		t = f.basename()[:-4]
		backupTimes.append(t)
backupTimes.sort(reverse=True)
for b in backupTimes:
	p = destination.join(b + ".zip", False)
	f = File(p, "r")
	backup = f.readJSON()
	backup["state"] = "uptodate"
	backups.append(backup)
	f.close()


def backup():
	global backups
	global destination
	timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
	currentZip = Archive(destination.join(timestamp + ".zip"), False, "w")
	backupType = "d"
	if len(backups) == 0:
		backupType = "b"
	currentBackup = {"files": {}, "folders": {}, "created": timestamp, "edited": timestamp, "type": backupType}

	for src in config["folders"]:
		isFolder = os.path.isdir(src)
		backupFolder(Path(src, isFolder), currentBackup, currentZip)

	folderStructure = {"files": {}, "folders": {}}
	for backup in backups:
		for file in backup["files"].keys():
			if file not in folderStructure["files"].keys():
				folderStructure["files"][file] = backup["files"][file]
		for folder in backup["folders"].keys():
			if folder not in folderStructure["folders"].keys():
				folderStructure["folders"][folder] = backup["folders"][folder]
	for file in folderStructure["files"].keys():
		if folderStructure["files"][file]["hash"] != "":
			if not Path(file, False).isfile():
				currentBackup["files"][file] = {"hash": "", "edited": ""}
	for folder in folderStructure["folders"].keys():
		if not Path(folder, True).isdir():
			currentBackup["folders"][folder] = False

	currentZip.writeString(json.dumps(currentBackup), currentBackup["created"] + ".json")

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
			del backup["state"]
			currentZip.writeString(json.dumps(backup, indent=4), backup["created"] + ".json")


def mergeInto(update, base):
	baseZip = Archive(destination.join(base["created"] + ".zip", False), "a")
	updateZip = Archive(destination.join(update["created"] + ".zip", False), "a")
	base["edited"] = update["edited"]
	for file in update["files"]:
		if update["files"][file]["hash"] == "":
			if base["type"] == "b":
				if file in base["files"].keys():
					del base["files"][file]
					base["state"] = "changed"
			else:
				base["files"][file] = update["files"][file]
				base["state"] = "changed"
			if file in baseZip.listdir():#TODO replace with contains for better performance
				baseZip.remove(file)
		else:
			base["files"][file] = update["files"][file]
			baseZip.writeString(updateZip.read(file), file)
			base["state"] = "changed"
	for folder in update["folders"].keys():
		exists = update["folders"][folder]
		if base["type"] == "b" and not exists:
			if folder in base["folders"].keys():
				del base["folders"][folder]
				base["state"] = "changed"
		else:
			base["folders"][folder] = exists
	baseZip.close()
	updateZip.close()
	destination.join(update["created"] + ".zip").rm()


def backupFolder(src, currentBackup, currentZip):
	global backups
	if src.isdir():
		filename = src.basename()
		for ignored in config["ignore"]:
			if filename == ignored:
				return
		for f in src.listdir():
			backupFolder(f, currentBackup, currentZip)
		while True:
			folderExists = -1
			for backup in backups:
				if src.path in backup["folders"].keys():
					if backup["folders"][src.path]:
						folderExists = 1
					else:
						folderExists = 0
					break
			if folderExists == -1 or folderExists == 0:
				currentBackup["folders"][src.path] = True
			if src.isroot() or folderExists == 1:
				break
			src = src.parent()
	elif src.isfile():
		filename = src.basename()
		for ignored in config["ignore"]:
			if filename == ignored:
				return
		storedHash = ""
		storedEdited = ""
		for backup in backups:
			if file in backup["files"].keys():
				storedHash = backup["files"][file]["hash"]
				storedEdited = backup["files"][file]["edited"]
				break
		if src.getmtime().strftime("%Y-%m-%dT%H:%M:%S") != storedEdited:
			f = File(src, "rb")
			sha256 = hashlib.sha256()
			while True:
				data = f.read(4096)
				if not data:
					break
				sha256.update(data)
			f.close()
			calculatedHash = sha256.hexdigest()
			if calculatedHash != storedHash:
				currentBackup["files"][src.path] = {"hash": calculatedHash, "edited": src.getmtime().strftime("%Y-%m-%dT%H:%M:%S")}
				currentZip.write(src, src.path)


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
