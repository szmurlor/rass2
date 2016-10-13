import os

from flask import g, abort, render_template
from rass_app import app
import storage
from utils import *


@app.route('/data/')
def datastore():
    if not g.user_id:
        abort(401)
    return render_template('datastore/datastore.html', scenarios=g.scenarios, uid=None)

@app.route('/data/new/', methods=['POST'])
def new_dataset(uid):
    if not g.user_id:
        abort(401)
    args = merge_http_request_arguments()
    return render_template('datastore/datastore.html', scenarios=g.scenarios, uid=uid)

@app.route('/data/delete/')
def delete_dataset(uid):
    if not g.user_id:
        abort(401)
    return render_template('datastore/datastore.html', scenarios=g.scenarios, uid=uid)

@app.route('/data/<uid>')
def dataset(uid):
    if not g.user_id:
        abort(401)
    return render_template('datastore/dataset.html', scenarios=g.scenarios, uid=uid)


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
