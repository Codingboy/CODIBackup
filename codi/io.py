import os.path
import shutil
import json
import datetime


class Path():
	def __init__(self, path, isFolder):
		self.path = os.path.abspath(os.path.expanduser(path))
		self.isFolder = isFolder
		if isFolder:
			if len(self.path) > 0:
				if self.path[-1] != os.sep:
					self.path += os.sep

	def __str__(self):
		return self.path

	def __repr__(self):
		return self.path

	def join(self, path, folder):
		p = path[0:]
		if p[0] == "/":
			p = p[1:]
		return Path(os.path.join(self.path, p), folder)

	def getmtime(self):
		return datetime.datetime.fromtimestamp(int(os.path.getmtime(self.path)))

	def exists(self):
		return os.path.exists(self.path)

	def getsize(self):
		return os.path.getsize(self.path)

	def isdir(self):
		return os.path.isdir(self.path)

	def isfile(self):
		return os.path.isfile(self.path)

	def islink(self):
		return os.path.islink(self.path)

	def ismount(self):
		return os.path.ismount(self.path)

	def drivename(self):
		drive = os.path.splitdrive(self.path)[0]
		if len(drive) > 2:
			drive = drive[:2]  #TODO test post fence error, should be length of 2
		return drive

	def nodrivename(self):
		if len(self.drivename()) > 0:
			return self.path[2:]
		return self.path

	def abspath(self):
		return self.path

	def parent(self):
		if self.isroot():
			return None
		if self.path[-1] == os.sep:
			return Path(os.path.dirname(self.path[:-1]), True)
		return Path(os.path.dirname(self.path), False)

	def isroot(self):
		if self.path == os.sep:
			return True
		if len(self.path) >= 2:
			if self.path[1] == ":":
				if len(self.path) == 2 or len(self.path) == 3:
					return True
		return False

	def listdir(self):
		ret = []
		if self.isdir():
			for f in os.listdir(self.path):
				path = os.path.join(self.path, f)
				if os.path.isfile(path):
					ret.append(Path(path, False))
				if os.path.isdir(path):
					path += os.sep
					ret.append(Path(path, True))
		return ret

	def basename(self):
		if self.path[-1] == os.sep:
			return os.path.basename(self.path[:-1]) + os.sep
		return os.path.basename(self.path)

	def relpath(self, path):
		ret = os.path.relpath(path.path, self.path)
		if path.path[-1] == os.sep:
			ret += os.sep
		return ret

	def cp(self, dst):
		if self.isdir():
			if not dst.exists():
				dst.mkdir()
			return shutil.copytree(self.path, dst.path)
		else:
			parentDir = dst.parent()
			if not parentDir.exists():
				parentDir.mkdir()
		return shutil.copy2(self.path, dst.path)

	def mv(self, dst):
		if self.isdir():
			if not dst.exists():
				dst.mkdir()
		else:
			parentDir = dst.parent()
			if not parentDir.exists():
				parentDir.mkdir()
		return shutil.move(self.path, dst.path)

	def rm(self):
		if self.isdir():
			return shutil.rmtree(self.path)
		return os.remove(self.path)

	def mkdir(self):
		return os.makedirs(self.path)


class File():
	def __init__(self, path, mode, encoding=None):
		self.path = path
		self.fd = None
		if "b" in mode:
			self.fd = open(self.path.path, mode)
		else:
			self.fd = open(self.path.path, mode, encoding=encoding)

	def close(self):
		return self.fd.close()

	def read(self, size=-1):
		return self.fd.read(size)

	def readline(self):
		return self.fd.readline()

	def write(self, data):
		return self.fd.write(data)

	def seek(self, offset, whence):
		return self.fd.seek(offset, whence)

	def tell(self):
		return self.fd.tell()

	def writeJSON(self, data):
		return json.dump(data, self.fd, indent=4)

	def readJSON(self):
		return json.load(self.fd)
