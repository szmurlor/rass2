from flask import request
from rass_app import app
import logger
import storage
from filesystem_helper import convert_to_unicode


def merge_http_request_arguments(log_args=False):
    # Parameters with the same name are overriten with the order:
    # QueryString
    # Form (POST)
    # File
    logger.debug("Merging following HTTP data:"
                 "\n- QueryString: %s" % request.args +
                 "\n- Form: %s" % request.form +
                 "\n- Files: %s" % request.files)

    args = {}
    for key, value in request.args.items():
        args[key] = value
        if log_args:
            app.logger.info("[GET]: %s -> %s" % (key, value))

    for key, value in request.form.items():
        args[key] = value
        if log_args:
            app.logger.info("[POST]: %s -> %s" % (key, value))

    for key, value in request.files.items():
        if log_args:
            app.logger.info("[FILE]: %s -> %s" % (key, value))
        content = convert_to_unicode(value.read())
        file_name = value.filename
        content_type = value.content_type
        content_length = len(content)

        if key not in args or content_length > 0:
            args[key] = storage.new_file_from_raw_bytes(content, file_name, content_type)

        if key in args and content_length is 0:
            uid = args[key]
            stored_file = storage.find_file_by_uid(uid)
            if stored_file is not None:
                args[key] = stored_file
                logger.debug("Uploaded file has no content, so we fetched the file using selected 'uid'\n" +
                             "Name: %s, uid: %s, stored_file: %s" % (key, uid, stored_file))
            else:
                # args[key] has the old value (maybe a not existing uid)
                logger.debug("Uploaded file has no content, the file selected using 'uid' doesn't exist.\n" +
                             "Name: %s, uid: %s, args[%s]: %s" % (key, uid, key, args[key]))

    return args
