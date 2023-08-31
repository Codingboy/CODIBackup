#!/usr/bin/env python3

import json
import hashlib
import os
from datetime import datetime, timezone, timedelta
import shutil
from argparse import ArgumentParser
from codi.io import Path, File
from logging import getLogger, DEBUG, FileHandler, StreamHandler, Formatter, INFO
from pathlib import PurePath
import traceback
from enum import Enum

__version__ = "0.0.1"

PROJECTNAME = "CODIBackup"
LOGNAME = PROJECTNAME + ".log"
LOGNAME = Path(os.path.abspath(__file__), False).parent().join(LOGNAME, False).path

logger = getLogger(PROJECTNAME)
logger.setLevel(DEBUG)
fh = FileHandler(LOGNAME)
fh.setLevel(DEBUG)
ch = StreamHandler()
ch.setLevel(DEBUG)
formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

VERBOSE = True
BACKUPS = []
CONFIG = {}
BACKUPROOT = None


class BackupType(str, Enum):
	Minute = "Minute"
	Hour = "Hour"
	Day = "Day"
	Week = "Week"
	Month = "Month"
	Year = "Year"
	Base = "Base"


def peek(timestring):
	timestamp = datetime.strptime(timestring, "%Y%m%dT%H%M%S")
	relevant = False
	folderStructure = {"files": {}, "folders": {}}
	for backup in BACKUPS:
		if not relevant:
			created = backup["created"]
			ts = datetime.strptime(created, "%Y%m%dT%H%M%S")
			if ts <= timestamp:
				relevant = True
		if relevant:
			for file in backup["files"].keys():
				if file not in folderStructure["files"].keys():
					if backup["files"][file]["hash"] != "":
						folderStructure["files"][file] = backup["created"] + file
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
			extract = False
			if toBeRecovered is not None:
				if file.startswith(toBeRecovered):
					extract = True
			else:
				extract = True
			if extract:
				tmp = file[file.find(os.sep) + 1:]
				tmp = tmp.replace(os.sep, "/")
				backupPath = BACKUPROOT.join(folderStructure["files"][file], False)
				originalPath = Path(file, False)
				backupPath.cp(originalPath)
				if VERBOSE:
					logger.info("extracting " + file)
					logger.debug(folderStructure["files"][file])
	for folder in folderStructure["folders"].keys():
		extract = False
		if toBeRecovered is not None:
			if folder.startswith(toBeRecovered):
				extract = True
		else:
			extract = True
		if extract:
			if not os.path.isdir(folder):
				os.makedirs(folder)


def createBackup():
	now = datetime.now()
	nowStr = now.strftime("%Y%m%dT%H%M%S")
	if len(BACKUPS) > 0:
		if now <= datetime.strptime(
		    BACKUPS[0]["created"],
		    "%Y%m%dT%H%M%S"):  #do not create backups if newer backup exists (just happens when system time is changed)
			return
	backupPath = BACKUPROOT.join(nowStr, True)
	backupPath.mkdir()
	backupType = BackupType.Minute
	if len(BACKUPS) == 0:
		backupType = BackupType.Base
	currentBackup = {"files": {}, "folders": {}, "created": nowStr, "edited": nowStr, "type": backupType}

	try:
		for src in CONFIG["folders"]:
			isFolder = os.path.isdir(src)
			backupFolder(Path(src, isFolder), currentBackup, backupPath)
	except IOError as e:
		logger.error(traceback.format_exc())
		backupPath.rm()
		if VERBOSE:
			logger.info("IOError: abort backup " + currentBackup["created"])
		return

	folderStructure = {"files": {}, "folders": {}}
	for backup in BACKUPS:
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

	if len(currentBackup["files"]) > 0 or len(currentBackup["folders"]) > 0:
		statePath = backupPath.join("CODIBackup_state.json", False)
		stateFile = File(statePath, "w")
		stateFile.writeJSON(currentBackup)
		stateFile.close()
		currentBackup["state"] = "uptodate"
		BACKUPS.insert(0, currentBackup)
		if VERBOSE:
			logger.info("created backup: " + currentBackup["created"])
	else:
		backupPath.rm()
		if VERBOSE:
			logger.info("empty backup: deleting " + currentBackup["created"])

	backupMinutes = CONFIG["minutes"]
	for backup in BACKUPS:
		backupType = backup["type"]
		if backupType == BackupType.Minute:
			created = datetime.strptime(backup["created"], "%Y%m%dT%H%M%S")
			if now > created + timedelta(minutes=backupMinutes * 1):
				backup["type"] = BackupType.Hour
				backup["state"] = "changed"
		else:
			break
	for i in reversed(range(len(BACKUPS))):
		backup = BACKUPS[i]
		backupType = backup["type"]
		if backupType == BackupType.Hour:
			while True:
				if i > 0:
					b = BACKUPS[i - 1]
					if b["type"] == backupType:
						created = datetime.strptime(backup["created"], "%Y%m%dT%H%M%S")
						edited = datetime.strptime(b["edited"], "%Y%m%dT%H%M%S")
						if edited < created + timedelta(minutes=59):
							mergeInto(b, backup)
							del BACKUPS[i - 1]
							i -= 1
						else:
							break
					else:
						break
				else:
					break
		elif backupType == BackupType.Minute:
			break

	backupHours = CONFIG["hours"]
	for backup in BACKUPS:
		backupType = backup["type"]
		if backupType == BackupType.Hour:
			created = datetime.strptime(backup["created"], "%Y%m%dT%H%M%S")
			if now > created + timedelta(hours=backupHours * 1) + timedelta(minutes=backupMinutes * 1):
				backup["type"] = BackupType.Day
				backup["state"] = "changed"
		else:
			break
	for i in reversed(range(len(BACKUPS))):
		backup = BACKUPS[i]
		backupType = backup["type"]
		if backupType == BackupType.Day:
			while True:
				if i > 0:
					b = BACKUPS[i - 1]
					if b["type"] == backupType:
						created = datetime.strptime(backup["created"], "%Y%m%dT%H%M%S")
						edited = datetime.strptime(b["edited"], "%Y%m%dT%H%M%S")
						if edited < created + timedelta(hours=23, minutes=59):
							mergeInto(b, backup)
							del BACKUPS[i - 1]
							i -= 1
						else:
							break
					else:
						break
				else:
					break
		elif backupType == BackupType.Hour or backupType == BackupType.Minute:
			break

	backupDays = CONFIG["days"]
	for backup in BACKUPS:
		backupType = backup["type"]
		if backupType == BackupType.Day:
			created = datetime.strptime(backup["created"], "%Y%m%dT%H%M%S")
			if now > created + timedelta(days=backupDays * 1) + timedelta(hours=backupHours * 1) + timedelta(minutes=backupMinutes * 1):
				backup["type"] = BackupType.Week
				backup["state"] = "changed"
		else:
			break
	for i in reversed(range(len(BACKUPS))):
		backup = BACKUPS[i]
		backupType = backup["type"]
		if backupType == BackupType.Week:
			while True:
				if i > 0:
					b = BACKUPS[i - 1]
					if b["type"] == backupType:
						created = datetime.strptime(backup["created"], "%Y%m%dT%H%M%S")
						edited = datetime.strptime(b["edited"], "%Y%m%dT%H%M%S")
						if edited < created + timedelta(days=6, hours=23, minutes=59):
							mergeInto(b, backup)
							del BACKUPS[i - 1]
							i -= 1
						else:
							break
					else:
						break
				else:
					break
		elif backupType == BackupType.Day or backupType == BackupType.Hour or backupType == BackupType.Minute:
			break

	backupWeeks = CONFIG["weeks"]
	for backup in BACKUPS:
		backupType = backup["type"]
		if backupType == BackupType.Week:
			created = datetime.strptime(backup["created"], "%Y%m%dT%H%M%S")
			if now > created + timedelta(days=backupDays * 1 + backupWeeks * 7) + timedelta(hours=backupHours *
			                                                                                1) + timedelta(minutes=backupMinutes * 1):
				backup["type"] = BackupType.Month
				backup["state"] = "changed"
		else:
			break
	for i in reversed(range(len(BACKUPS))):
		backup = BACKUPS[i]
		backupType = backup["type"]
		if backupType == BackupType.Month:
			while True:
				if i > 0:
					b = BACKUPS[i - 1]
					if b["type"] == backupType:
						created = datetime.strptime(backup["created"], "%Y%m%dT%H%M%S")
						edited = datetime.strptime(b["edited"], "%Y%m%dT%H%M%S")
						if edited < created + timedelta(days=27, hours=23, minutes=59):
							mergeInto(b, backup)
							del BACKUPS[i - 1]
							i -= 1
						else:
							break
					else:
						break
				else:
					break
		elif backupType == BackupType.Week or backupType == BackupType.Day or backupType == BackupType.Hour or backupType == BackupType.Minute:
			break

	backupMonths = CONFIG["months"]
	for backup in BACKUPS:
		backupType = backup["type"]
		if backupType == BackupType.Month:
			created = datetime.strptime(backup["created"], "%Y%m%dT%H%M%S")
			if now > created + timedelta(days=backupDays * 1 + backupWeeks * 7 +
			                             backupMonths * 28) + timedelta(hours=backupHours * 1) + timedelta(minutes=backupMinutes * 1):
				backup["type"] = BackupType.Year
				backup["state"] = "changed"
		else:
			break
	for i in reversed(range(len(BACKUPS))):
		backup = BACKUPS[i]
		backupType = backup["type"]
		if backupType == BackupType.Year:
			while True:
				if i > 0:
					b = BACKUPS[i - 1]
					if b["type"] == backupType:
						created = datetime.strptime(backup["created"], "%Y%m%dT%H%M%S")
						edited = datetime.strptime(b["edited"], "%Y%m%dT%H%M%S")
						if edited < created + timedelta(days=28 * 12 - 1, hours=23, minutes=59):
							mergeInto(b, backup)
							del BACKUPS[i - 1]
							i -= 1
						else:
							break
					else:
						break
				else:
					break
		elif backupType == BackupType.Month or backupType == BackupType.Week or backupType == BackupType.Day or backupType == BackupType.Hour or backupType == BackupType.Minute:
			break

	backupYears = CONFIG["years"]
	for backup in BACKUPS:
		backupType = backup["type"]
		if backupType == BackupType.Year:
			created = datetime.strptime(backup["created"], "%Y%m%dT%H%M%S")
			if now > created + timedelta(days=backupDays * 1 + backupWeeks * 7 + backupMonths * 28 +
			                             backupYears * 12 * 28) + timedelta(hours=backupHours * 1) + timedelta(minutes=backupMinutes * 1):
				backup["type"] = BackupType.Base
				backup["state"] = "changed"
		else:
			break
	for i in reversed(range(len(BACKUPS))):
		backup = BACKUPS[i]
		backupType = backup["type"]
		if backupType == BackupType.Base:
			while True:
				if i > 0:
					b = BACKUPS[i - 1]
					if b["type"] == backupType:
						mergeInto(b, backup)
						del BACKUPS[i - 1]
						i -= 1
					else:
						break
				else:
					break
		elif backupType == BackupType.Year or backupType == BackupType.Month or backupType == BackupType.Week or backupType == BackupType.Day or backupType == BackupType.Hour or backupType == BackupType.Minute:
			break

	for backup in BACKUPS:
		if backup["state"] == "changed":
			del backup["state"]
			backupStatePath = BACKUPROOT.join(backup["created"], True).join("CODIBackup_state.json", False)
			backupStatePath.rm()
			backupStateFile = File(backupStatePath, "w")
			backupStateFile.writeJSON(backup)
			backupStateFile.close()
			if VERBOSE:
				logger.info("rewrite " + backup["created"] + "/CODIBackup_state.json with type=" + backup["type"])


def mergeInto(update, base):
	if VERBOSE:
		logger.info("merging " + update["created"] + " into " + base["created"])
	base["edited"] = update["edited"]
	base["state"] = "changed"
	for file in update["files"]:
		if update["files"][file]["hash"] == "":
			fileExists = False
			if file in base["files"].keys():
				if base["files"][file]["hash"] != "":
					fileExists = True
			if base["type"] == BackupType.Base:
				#if file in base["files"].keys():
				del base["files"][file]
				base["state"] = "changed"
			else:
				base["files"][file] = update["files"][file]
				base["state"] = "changed"
			if fileExists:
				basePath = BACKUPROOT.join(base["created"], True)
				filePath = basePath.join(file, False)  #TODO os
				filePath.rm()
				parent = filePath.parent()
				while True:
					if parent.path == basePath.path:
						break
					if len(parent.listdir()) == 0:
						parent.rm()
					else:
						break
					parent = parent.parent()
				logger.info("remove " + file + " from " + base["created"])
		else:
			# if file in base["files"].keys():
			# 	if base["files"][file]["hash"] != "":
			# 		pass
			base["files"][file] = update["files"][file]
			srcPath = BACKUPROOT.join(update["created"], True).join(file, False)  #TODO os
			dstPath = BACKUPROOT.join(base["created"], True).join(file, False)  #TODO os
			srcPath.mv(dstPath)
			base["state"] = "changed"
	for folder in update["folders"].keys():
		exists = update["folders"][folder]
		if base["type"] == BackupType.Base and not exists:
			if folder in base["folders"].keys():
				del base["folders"][folder]
				base["state"] = "changed"
		else:
			base["folders"][folder] = exists
	BACKUPROOT.join(update["created"], True).rm()


def backupFolder(src, currentBackup, backupPath):
	if src.isdir():
		filename = src.basename()
		for ignored in CONFIG["ignore"]:
			if PurePath(src.path).match(ignored):
				return
		for f in src.listdir():
			backupFolder(f, currentBackup, backupPath)
		while True:
			folderExists = -1
			for backup in BACKUPS:
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
		for ignored in CONFIG["ignore"]:
			if PurePath(src.path).match(ignored):
				return
		storedHash = ""
		storedEdited = ""
		for backup in BACKUPS:
			if src.path in backup["files"].keys():
				storedHash = backup["files"][src.path]["hash"]
				storedEdited = backup["files"][src.path]["edited"]
				break
		if src.getmtime().strftime("%Y%m%dT%H%M%S") != storedEdited:
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
				currentBackup["files"][src.path] = {"hash": calculatedHash, "edited": src.getmtime().strftime("%Y%m%dT%H%M%S")}
				src.cp(backupPath.join(src.path, False))
				if VERBOSE:
					logger.info("backing up " + src.path)


if __name__ == "__main__":
	try:
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
		VERBOSE = args.verbose

		configPath = Path(os.path.abspath(__file__), False).parent().join("config.json", False)
		if args.config is not None:
			configPath = Path(os.path.abspath(os.path.expanduser(args.configPath)), False)

		f = File(configPath, "r")
		CONFIG = f.readJSON()
		f.close()

		BACKUPROOT = Path(CONFIG["backupRoot"], True)
		if not BACKUPROOT.isdir():
			BACKUPROOT.mkdir()

		backupTimes = []
		for f in BACKUPROOT.listdir():
			if f.isdir():  #TODO exclude softlink folders
				backupTimes.append(f.basename())
		backupTimes.sort(reverse=True)
		for b in backupTimes:
			# if VERBOSE:
			# 	logger.debug("loading " + b.path)
			statePath = BACKUPROOT.join(b, True).join("CODIBackup_state.json", False)
			stateFile = File(statePath, "r")
			ba = json.loads(stateFile.read())
			stateFile.close()
			ba["state"] = "uptodate"
			# if VERBOSE:
			# 	logger.debug(ba["type"])
			BACKUPS.append(ba)
		# logger.debug(BACKUPS)

		if args.backup:
			createBackup()
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
	except Exception as e:
		logger.error(traceback.format_exc())
