known_extensions = {
	'.zip': 'application/zip',
	'.rar': 'application/rar',
	'.tgz': 'application/tgz',
	'.7z' : 'application/7zip',
	'.dcm': 'application/dicom',
	'.jpg': 'image/jpg',
	'.png': 'image/png',
	'.gif': 'image/gif',
	'.bmp': 'image/bmp',
	'.out': 'text/out',
	'.txt': 'text/plain'
}

def get_content_type_by_extension(extension):
	return known_extensions.get(extension, None)

def is_archive(content_type):
	archive_content_types = ['application/zip', 'application/rar', 'application/tgz', 'application/7zip']
	return content_type in archive_content_types
