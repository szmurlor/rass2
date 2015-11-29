import zipfile
import os

class ZIPArchiveExtractor(object):
	def extract(self, file_path, output_path=None):
		if output_path is None:
			output_path, _ = os.path.split(file_path)
		with open(file_path, 'rb') as f:
			z = zipfile.ZipFile(f)
			for name in z.namelist():
    				z.extract(name, output_path)
		return output_path

class RARArchiveExtractor(object):
	pass

class TGZArchiveExtractor(object):
	pass
