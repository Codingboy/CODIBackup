from codi.codizipfile import ZipFile, ZIP_DEFLATED
from codi.codiio import Path, File
import datetime


class Archive:
	def __init__(self, path, mode, compression=ZIP_DEFLATED):
		self.path = path
		self.mode = mode
		self.zf = self._open(path, mode, mode)

	def _open(self, path, mode, compression=ZIP_DEFLATED):
		self.zf = ZipFile(path.path, mode, compression=8)
		return self.zf

	def write(self, path, arcname=None, compress_type=None, compresslevel=None):
		#self._mkdirs(arcname)
		self.zf.write(path.path, arcname, compress_type, compresslevel)

	def writeString(self, data, path, compress_type=None, compresslevel=None):
		#self._mkdirs(path)
		self.zf.writestr(path, data, compress_type, compresslevel)

	def mkdir(self, dst):
		self.zf.mkdir(dst)

	def _mkdirs(self, dirs):
		if len(dirs) > 0:
			if dirs[0] == "/":
				dirs = dirs[1:]
			d = ""
			while True:
				if "/" not in dirs:
					break
				d += dirs[:dirs.find("/")]
				self.mkdir(d)
				dirs = dirs[dirs.find("/") + 1:]

	def getmtime(self, src):
		timestamp = self.zf.getinfo(src).date_time
		return datetime.datetime(year=timestamp[0],
		                         month=timestamp[1],
		                         day=timestamp[2],
		                         hour=timestamp[3],
		                         minute=timestamp[4],
		                         second=timestamp[5])

	def remove(self, path):
		return self.zf.remove(path)  #https://stackoverflow.com/questions/513788/delete-file-from-zipfile-with-the-zipfile-module

	def extract(self, src, dst, password=None):
		return self.zf.extract(src, dst, password)

	def read(self, src, password=None):
		return self.zf.read(src, password)

	def close(self):
		self.zf.close()

	def listdir(self):
		ret = []
		for info in self.zf.infolist():
			path = info.filename
			if info.is_dir():
				path += "/"
			ret.append(path)
		return ret
