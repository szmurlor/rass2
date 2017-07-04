# -*- encoding: utf-8
import os

from datetime import datetime
from flask import g, abort, render_template, flash, redirect
from werkzeug.utils import secure_filename

import database
import rass_app
from rass_app import app
from utils import *
import uuid


@app.route('/data/')
def datastore():
    if not g.user_id:
        abort(401)

    datasets = database.Dataset.query.filter_by(deleted=False).order_by(database.Dataset.date_created)
    dataset_types = database.DatasetType.query.order_by(database.DatasetType.name)
    return render_template('datastore/datastore.html', scenarios=g.scenarios, uid=None, datasets=datasets,
                           now=datetime.utcnow(), dataset_types=dataset_types)


@app.route('/data/update', methods=['POST'])
def update_dataset():
    if not g.user_id:
        abort(401)
    args = merge_http_request_arguments(True)

    user = database.User.query.filter_by(id=g.user_id).one()
    dataset = database.Dataset.query.filter_by(id=int(args['dataset_id'])).one()
    dataset.short_notes = args['short_notes']
    dataset.long_notes = args['long_notes']
    dataset.name = args['name']
    dataset.user_modified = user
    date_created = datetime.strptime(args['date_created'], '%d.%m.%Y')
    dataset.date_created = date_created
    dataset.date_modified = datetime.utcnow()
    database.db.session.add(dataset)
    database.db.session.commit()

    return render_template('datastore/dataset.html', scenarios=g.scenarios, uid=dataset.id, dataset=dataset)


@app.route('/data/add', methods=['POST'])
def new_dataset():
    if not g.user_id:
        abort(401)
    args = merge_http_request_arguments(True)

    user = database.User.query.filter_by(id=g.user_id).one()
    dataset_type = database.DatasetType.query.filter_by(id=int(args['dataset_type'])).one()
    dataset = database.Dataset(name=args['name'], user_created=user)
    dataset.short_notes = args['short_notes']
    dataset.long_notes = rass_app.LONG_NOTES
    dataset.user_modified = user
    date_created = datetime.strptime(args['date_created'], '%d.%m.%Y')
    dataset.date_created = date_created
    dataset.type = dataset_type
    database.db.session.add(dataset)
    database.db.session.commit()

    return render_template('datastore/dataset.html', scenarios=g.scenarios, uid=dataset.id, dataset=dataset)


@app.route('/data/delete/')
def delete_dataset(uid):
    if not g.user_id:
        abort(401)
    return render_template('datastore/datastore.html', scenarios=g.scenarios, uid=uid)

def allowed_file(filename):
#    return '.' in filename and \
#           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
    return True


@app.route('/data/upload/', methods=['POST', 'GET'])
def upload_file():
    if not g.user_id:
        abort(401)

    args = {}
    for key, value in request.form.iteritems():
        args[key] = value  # it is OK to overwrite QueryString parameters
        app.logger.info("[POST]: %s -> %s" % (key, value))

    user = database.User.query.filter_by(id=g.user_id).one()
    dataset = database.Dataset.query.filter_by(id=int(args['dataset_id'])).one()
    file_type = args['file_type']
    parent_uid = None
    if args['parent_id'] is not None and len(args['parent_id']) > 0:
        parent_uid = int(args['parent_id'])

    # check if the post request has the file part
    if 'file' not in request.files:
        flash(u'No file part', 'Error')
        return redirect(request.url)
    file = request.files['file']

    # if user does not select file, browser also
    # submit a empty part without filename
    if file.filename == '':
        flash(u'Nie wybrano żadnego pliku.', 'error')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        # Zapisuje plik w repozytorium plików pod 'bezpieczną' nazwą:
        # nazwa_oryginalna_uuid4
        # repozytorium plików to zdefiniowany folder w rass_app.
        if parent_uid is not None:
            parent_file = database.StoredFile.query.filter_by(uid=parent_uid).one_or_none()
        else:
            parent_file = None

        filename = secure_filename("%s_%s" % (file.filename, str(uuid.uuid4())))
        datefolder = datetime.utcnow().strftime('%Y-%m-%d')
        uploadpath = os.path.join(app.config['UPLOAD_FOLDER'], datefolder)
        if not os.path.isdir(uploadpath):
            os.mkdir(uploadpath)
        fullpath_filename = os.path.join(uploadpath, filename)
        file.save(fullpath_filename)


        # Zapamiętuję plik w bazie danych
        stored_file = database.StoredFile(fullpath_filename, None)
        stored_file.dataset = dataset
        stored_file.type = file_type
        stored_file.name = file.filename
        stored_file.description = args['description']
        stored_file.stored_at = datetime.utcnow()
        stored_file.stored_by = user
        stored_file.parent = parent_file

        # Generate token
        stored_file.token = str(uuid.uuid4()).replace("-", "")

        database.db.session.add(stored_file)
        database.db.session.commit()

        flash(u'Pobrałem plik o nazwie: %s' % file.filename, 'success')

    return render_template('datastore/dataset.html', scenarios=g.scenarios, uid=dataset.id, dataset=dataset)


@app.route('/data/delete/<uid>', methods=['GET'])
def delete_file(uid):
    if not g.user_id:
        abort(401)

    dataset = None

    stored_file = database.StoredFile.query.filter_by(uid=uid).one()
    if stored_file is not None:
        dataset = stored_file.dataset

        file_name = stored_file.name
        #os.remove(stored_file.path)
        #database.db.session.delete(stored_file)

        stored_file.deleted = True
        database.db.session.add(stored_file)
        database.db.session.commit()

        flash(u"Poprawnie usunąłem plik %s" % file_name, 'success')

    return render_template('datastore/dataset.html', scenarios=g.scenarios, uid=dataset.id, dataset=dataset)

@app.route('/data/update_comment', methods=['POST', 'GET'])
def update_comment():
    if not g.user_id:
        abort(401)

    dataset = None

    args = merge_http_request_arguments(True)
    file_id = int(args['file_id'])
    new_comment = args['comment']

    stored_file = database.StoredFile.query.filter_by(uid=file_id).one()
    if stored_file is not None:
        dataset = stored_file.dataset

        file_name = stored_file.name
        stored_file.description = new_comment
        database.db.session.add(stored_file)
        database.db.session.commit()

        flash(u"Zaktualizowałem komentarz do pliku %s na wartość: '%s'" % (file_name, new_comment), 'success')

    return render_template('datastore/dataset.html', scenarios=g.scenarios, uid=dataset.id, dataset=dataset)


@app.route('/data/<dsid>')
def dataset(dsid):
    if not g.user_id:
        abort(401)

    dataset = database.Dataset.query.filter_by(id=dsid).one()

    return render_template('datastore/dataset.html', scenarios=g.scenarios, uid=dsid, dataset=dataset)


@app.route('/fs/<uid>')
def download(uid):
    if not g.user_id:
        abort(401)

    stored_file = storage.find_file_by_uid(uid)
    if stored_file is None:
        return render_template("no_file.html", uid=uid), 404

    content = stored_file.read(charset=None)
    return content, 200, {
        'Content-Type': stored_file.content_type,
        'Content-Disposition': "attachment; filename=" + stored_file.name
    }

@app.route('/fs/token/<token>')
def download_token(token):
    stored_file = storage.find_file_by_token(token)

    if stored_file is None:
        return render_template("no_file.html", uid=token), 404

    content = stored_file.read(charset=None)
    return content, 200, {
        'Content-Type': stored_file.content_type,
        'Content-Disposition': "attachment; filename=" + stored_file.name.encode('utf-8')
    }
