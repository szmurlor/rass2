import os

from datetime import datetime
from flask import g, abort, render_template

import database
from rass_app import app
from utils import *


@app.route('/data/')
def datastore():
    if not g.user_id:
        abort(401)

    datasets = database.Dataset.query.order_by(database.Dataset.date_created)
    dataset_types = database.DatasetType.query.order_by(database.DatasetType.name)
    return render_template('datastore/datastore.html', scenarios=g.scenarios, uid=None, datasets=datasets,
                           now=datetime.utcnow(), dataset_types=dataset_types)


@app.route('/data/add', methods=['POST'])
def new_dataset():
    if not g.user_id:
        abort(401)
    args = merge_http_request_arguments(True)

    user = database.User.query.filter_by(id=g.user_id).one()
    dataset = database.Dataset(name=args['name'], user_created=user)
    dataset.short_notes = args['short_notes']
    dataset.user_modified = user
    date_created = datetime.strptime(args['date_created'], '%d.%m.%Y');
    dataset.date_created = date_created
    database.db.session.add(dataset)
    database.db.session.commit()

    return render_template('datastore/dataset.html', scenarios=g.scenarios, uid=dataset.id, dataset=dataset)


@app.route('/data/delete/')
def delete_dataset(uid):
    if not g.user_id:
        abort(401)
    return render_template('datastore/datastore.html', scenarios=g.scenarios, uid=uid)


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

    file_name = os.path.basename(stored_file.path)
    content = stored_file.read(charset=None)
    return content, 200, {
        'Content-Type': stored_file.content_type,
        'Content-Disposition': "attachment; filename=" + file_name
    }
