#!/usr/bin/env python3

import json
import hashlib
import os
from datetime import datetime, timezone, timedelta
import shutil
from argparse import ArgumentParser
from codi.codiio import Path, File
from codi.codiar import Archive
from logging import getLogger, DEBUG, FileHandler, StreamHandler, Formatter
from pathlib import PurePath

__version__ = "0.0.1"

PROJECTNAME = "CODIBackup"
LOGNAME = PROJECTNAME + ".log"

logger = getLogger(PROJECTNAME)
logger.setLevel(DEBUG)
#fh = FileHandler(LOGNAME)
#fh.setLevel(DEBUG)
ch = StreamHandler()
ch.setLevel(DEBUG)
formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#fh.setFormatter(formatter)
ch.setFormatter(formatter)
#logger.addHandler(fh)
logger.addHandler(ch)


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
					if backup["files"][file]["hash"] != "":
						folderStructure["files"][file] = backup["created"] + ".zip" + file
					else:
						folderStructure["files"][file] = ""
			for folder in backup["folders"].keys():
				if folder not in folderStructure["folders"].keys():
					if backup["folders"][folder]:
						folderStructure["folders"][folder] = folder
	return folderStructure


def recover(timestring, toBeRecovered=None):
	folderStructure = peek(timestring)
	for file in folderStructure["files"].keys():
		if file != "":
			extract = True
			if toBeRecovered is not None:
				if file.startswith(toBeRecovered):
					extract = True
			if extract:
				archive = folderStructure["files"][file][:folderStructure["files"][file].find("/")]
				ar = Archive(destination.join(archive, False), "r")
				ar.extract(file[file.find("/") + 1:], file[:file.find("/")])
				if verbose:
					logger.info("extracting " + file)
				ar.close()
	for folder in folderStructure["folders"].keys():
		extract = True
		if toBeRecovered is not None:
			if folder.startswith(toBeRecovered):
				extract = True
		if extract:
			if not os.path.isdir(folder):
				os.makedirs(folder)


def backup():
	global backups
	global destination
	timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
	currentZip = Archive(destination.join(timestamp + ".zip", False), "w")
	backupType = "min"
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

	currentZip.writeString(json.dumps(currentBackup, indent=4), "state.json")
	currentZip.close()
	backups.insert(0, currentBackup)
	if verbose:
		logger.info("backup created")

	backupMinutes = config["minutes"]
	for backup in backups:
		backupType = backup["type"]
		if backupType == "min":
			created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
			if datetime.now() > created + timedelta(minutes=backupMinutes * 1):
				backup["type"] = "h"
				backup["state"] = "changed"
		else:
			break
	for i in reversed(range(len(backups))):
		backup = backups[i]
		backupType = backup["type"]
		if backupType == "h":
			while True:
				if i > 0:
					b = backups[i - 1]
					if b["type"] == backupType:
						created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
						edited = datetime.strptime(b["edited"], "%Y-%m-%dT%H:%M:%S")
						if edited < created + timedelta(minutes=60):
							mergeInto(b, backup)
							del backups[i - 1]
							i -= 1
						else:
							break
					else:
						break
				else:
					break
		elif backupType == "min":
			break

	backupHours = config["hours"]
	for backup in backups:
		backupType = backup["type"]
		if backupType == "h":
			created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
			if datetime.now() > created + timedelta(hours=backupHours * 1) + timedelta(minutes=backupMinutes * 1):
				backup["type"] = "d"
				backup["state"] = "changed"
		else:
			break
	for i in reversed(range(len(backups))):
		backup = backups[i]
		backupType = backup["type"]
		if backupType == "d":
			while True:
				if i > 0:
					b = backups[i - 1]
					if b["type"] == backupType:
						created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
						edited = datetime.strptime(b["edited"], "%Y-%m-%dT%H:%M:%S")
						if edited < created + timedelta(hours=24):
							mergeInto(b, backup)
							del backups[i - 1]
							i -= 1
						else:
							break
					else:
						break
				else:
					break
		elif backupType == "h":
			break

	backupDays = config["days"]
	for backup in backups:
		backupType = backup["type"]
		if backupType == "d":
			created = datetime.strptime(backup["created"], "%Y-%m-%dT%H:%M:%S")
			if datetime.now() > created + timedelta(days=backupDays * 1) + timedelta(hours=backupHours *
			                                                                         1) + timedelta(minutes=backupMinutes * 1):
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
			if datetime.now() > created + timedelta(days=backupDays * 1 + backupWeeks * 7) + timedelta(hours=backupHours * 1) + timedelta(
			    minutes=backupMinutes * 1):
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
			if datetime.now() > created + timedelta(days=backupDays * 1 + backupWeeks * 7 + backupMonths * 28) + timedelta(
			    hours=backupHours * 1) + timedelta(minutes=backupMinutes * 1):
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
			if datetime.now() > created + timedelta(days=backupDays * 1 + backupWeeks * 7 + backupMonths * 28 + backupYears * 12 *
			                                        28) + timedelta(hours=backupHours * 1) + timedelta(minutes=backupMinutes * 1):
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
			currentZip = Archive(destination.join(backup["created"] + ".zip", False), "a")
			currentZip.remove("state.json")
			currentZip.writeString(json.dumps(backup, indent=4), "state.json")
			currentZip.close()


def mergeInto(update, base):
	if verbose:
		logger.info("merging " + update["created"] + " into " + base["created"])
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
			if file in baseZip.listdir():  #TODO replace with contains for better performance
				baseZip.remove(file[file.find("/") + 1:])
		else:
			if file in base["files"].keys():
				if base["files"][file]["hash"] != "":
					baseZip.remove(file[file.find("/") + 1:])
			base["files"][file] = update["files"][file]
			baseZip.writeString(updateZip.read(file[file.find("/") + 1:]), file[file.find("/") + 1:])
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
	destination.join(update["created"] + ".zip", False).rm()


def backupFolder(src, currentBackup, currentZip):
	global backups
	if src.isdir():
		filename = src.basename()
		for ignored in config["ignore"]:
			#if filename == ignored:
			if PurePath(src.path).match(ignored):
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
			#if filename == ignored:
			if PurePath(src.path).match(ignored):
				return
		storedHash = ""
		storedEdited = ""
		for backup in backups:
			if src.path in backup["files"].keys():
				storedHash = backup["files"][src.path]["hash"]
				storedEdited = backup["files"][src.path]["edited"]
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
				currentZip.write(src, src.path[src.path.find("/") + 1:])
				if verbose:
					logger.info("backing up " + src.path)


destination = None
backups = []
verbose = False
if __name__ == "__main__":
	PROJECTNAME = "CODIBackup"

	__version__ = "0.1.0"

	parser = ArgumentParser()
	parser.add_argument("-v", "--verbose", action="store_true", help="prints what is done")
	parser.add_argument("-b", "--backup", action="store_true", help="creates a backup")
	parser.add_argument("-p", "--peek", help="lists all files from a backup")
	parser.add_argument("-r", "--recover", help="recovers a specific state from the backups")
	parser.add_argument("-a", "--all", action="store_true", help="sets flag to restore everything")
	parser.add_argument("-s", "--selection", help="select file or folder to be recovered")
	parser.add_argument("-c", "--config", help="specify a configfile")
	args = parser.parse_args()
	valid = False
	verbose = args.verbose

	configfile = Path(os.path.abspath(__file__), False).parent().join("config.json", False)
	if args.config is not None:
		configfile = Path(os.path.abspath(os.path.expanduser(args.configfile)), False)

	f = File(configfile, "r")  #TODO change to .config dir
	config = f.readJSON()
	f.close()

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
		if verbose:
			logger.info("loading " + p.path)
		ar = Archive(p, "r")
		ba = json.loads(ar.read("state.json"))
		ba["state"] = "uptodate"
		backups.append(ba)
		ar.close()

	if args.backup:
		backup()
		valid = True
	else:
		if args.peek is not None:
			folderStructure = peek(args.peek)
			for file in folderStructure["files"].keys():
				print(folderStructure["files"][file])
			valid = True
		elif args.recover is not None:
			toBeRecovered = None
			if args.all is not None:
				recover(args.recover, toBeRecovered)
				valid = True
			else:
				if args.selection is not None:
					toBeRecovered = args.selection
					recover(args.recover, toBeRecovered)
					valid = True
	if not valid:
		parser.print_help()
