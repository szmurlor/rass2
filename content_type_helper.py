from archive_extractor import *

known_extensions = {
	'.zip': 'application/zip',
	'.rar': 'application/x-rar-compressed',
	'.tgz': 'application/gzip',
	'.7z' : 'application/x-7z-compressed',
	'.dcm': 'application/dicom',
	'.jpg': 'image/jpg',
	'.png': 'image/png',
	'.gif': 'image/gif',
	'.bmp': 'image/bmp',
	'.out': 'text/plain',
	'.txt': 'text/plain'
}

archive_content_types = {
	'application/zip' : ZIPArchiveExtractor,
	'application/gzip' : TGZArchiveExtractor,
	'application/x-rar-compressed' : RARArchiveExtractor,
	'application/x-7z-compressed': None
}

def get_content_type_by_extension(extension):
	return known_extensions.get(extension, None)

def get_archive_extractor(content_type):
	return archive_content_types.get(content_type, None)

def is_archive(content_type):
	return content_type in archive_content_types
