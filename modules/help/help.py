# -*- encoding: utf-8
import os

from datetime import datetime
from flask import g, abort, render_template, flash, redirect

import database
import rass_app
from rass_app import app
from utils import *


@app.route('/help/')
def help():
    if not g.user_id:
        abort(401)
    return render_template('help/help.html', scenarios=g.scenarios, uid=None, now=datetime.utcnow())

@app.route('/help/coi_new_dataset')
def coi_new_dataset():
    if not g.user_id:
        abort(401)

    mcontent = open('doc/coi_new_dataset/doc.md', 'r').read()
    return render_template('help/help_doc.html', mcontent=mcontent, scenarios=g.scenarios, uid=None, now=datetime.utcnow())
