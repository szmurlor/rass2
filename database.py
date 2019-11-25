# -*- coding: utf-8
import json
import os.path
import uuid

from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import DateTime

import content_type_helper
import filesystem_helper
from hashlib import sha512
from random import choice
from string import ascii_lowercase, digits
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from rass_app import app
import flask_sqlalchemy 

print(dir(flask_sqlalchemy))
db = SQLAlchemy(app)
db.session.expire_on_commit = False

def get_engine():
    return db.get_engine()


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(128))
    salt = db.Column(db.String(5))
    home = db.Column(db.String(64), unique=True)

    def __init__(self, username, root='/tmp'):
        self.username = username
        self.home = '%s/%s' % (root, username)

    def set_password(self, password, salt=None):
        if salt is None:
            salt = ''.join(choice(ascii_lowercase + digits) for x in range(10))
        self.password = sha512((salt + password).encode("utf-8")).hexdigest()
        self.salt = salt

    def __repr__(self):
        return '<User %r>' % self.username


class UserSessionData(db.Model):
    uid = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    key = db.Column(db.String(32))
    value = db.Column(db.Binary())

    def __init__(self, key, value, user_id):
        self.user_id = user_id
        self.key = key
        self.value = value


class Dataset(db.Model):
    __tablename__ = 'dataset'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))

    date_created = db.Column(db.DateTime())
    user_created_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user_created = relationship("User", back_populates="datasets_created", foreign_keys=[user_created_id])

    date_modified = db.Column(db.DateTime())
    user_modified_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user_modified = relationship("User", back_populates="datasets_modified", foreign_keys=[user_modified_id])

    type_id = db.Column(db.Integer, db.ForeignKey("dataset_type.id"))
    type = relationship("DatasetType", back_populates="datasets", foreign_keys=[type_id])

    short_notes = db.Column(db.String(255))
    long_notes = db.Column(db.String(8192))

    deleted = db.Column(db.Boolean, default=False)

    def __init__(self, name, user_created):
        self.user_created = user_created
        self.name = name
        self.date_created = datetime.utcnow()
        self.date_modified = self.date_created
        self.user_modified = user_created

    def files_by_type(self, file_type_name, parent_uid=None):
        result = []

        for f in self.files:
            if f.deleted is False and f.type.lower() == file_type_name.lower():
                if parent_uid is None:
                    result.append(f)
                else:
                    if f.parent is not None and f.parent.uid == parent_uid:
                        result.append(f)

        return sorted(result, key=lambda x: x.is_archived())

    def get_file_type(self, type_name):       
        return self.type.get_file_type(type_name)

User.datasets_modified = relationship("Dataset", order_by=Dataset.id, back_populates="user_modified", foreign_keys=[Dataset.user_modified_id])
User.datasets_created = relationship("Dataset", order_by=Dataset.id, back_populates="user_created", foreign_keys=[Dataset.user_created_id])


class DatasetType(db.Model):
    __tablename__ = 'dataset_type'
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(128))
    file_types = db.Column(db.String(8192))

    def __init__(self, name):
        self.name = name

    def file_types_list(self, parent):
        config = json.loads(self.file_types)
        res = []
        for type in config['types']:
            if 'parent_type' not in type or type['parent_type'] == parent:
                res.append(type)
        return res

    def get_file_types(self):
        return json.loads(self.file_types)

    def get_file_type(self, type_name):        
        config = json.loads(self.file_types)
        for type in config['types']:
            if type["name"] == type_name:
                return type
        return None


DatasetType.datasets = relationship("Dataset", order_by=Dataset.id, back_populates="type",
                                    foreign_keys=[Dataset.type_id])


class StoredFile(db.Model):
    uid = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(512))
    name = db.Column(db.String(128))
    description = db.Column(db.String(512))
    content_type = db.Column(db.String(32))
    type = db.Column(db.String(128))

    stored_at = db.Column(db.DateTime(), default=datetime.utcnow)
    stored_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    stored_by = relationship("User", foreign_keys=[stored_by_id])

    dataset_id = db.Column(db.Integer, db.ForeignKey("dataset.id"))
    dataset = relationship("Dataset", back_populates="files")

    deleted = db.Column(db.Boolean, default=False)

    token = db.Column(db.String(128))
    meta = db.Column(db.String(4096))

    def __init__(self, file_path, content_type=None):
        directory, name = os.path.split(file_path)

        if len(name) > 0:
            name, extension = os.path.splitext(name)
            self.name = name
            self.path = os.path.join(directory, name + extension)

            if content_type is None:
                content_type = content_type_helper.get_content_type_by_extension(extension)
                if content_type is None:
                    content_type = 'application/octet-stream'
            self.content_type = content_type
        else:  # path is a directory (ends with '/')
            self.name = os.path.join(os.path.basename(directory), '')
            self.path = directory
            self.content_type = 'inode/directory'

    def read(self, charset='latin2'):
        with open(self.path, 'rb') as f:
            raw_bytes = f.read()
            if charset:
                return raw_bytes.decode(charset)
            return raw_bytes

    def __repr__(self):
        return '<StoredFile (uid: %s, name:"%s", path:"%s") %s>' % (self.uid, self.name, self.path, self.content_type)

    def __str__(self):
        return self.path

    def _get_meta(self):
        res = {}
        if self.meta is not None:
            try:
                res.update(json.loads(self.meta))
            except e:
                app.logger.info("[ERROR]: Error converting meta data for StoreFile id: %d" % self.uid)
        return res
            
    def _update_meta(self, meta_as_dict):
        self.meta = json.dumps(meta_as_dict);

    def has_meta_value(self, key):
        m = self._get_meta()
        return key in m

    def get_meta_value(self, key):
        m = self._get_meta()
        if key in m:
            return m[key]
        return None

    def set_meta_value(self, key, value):
        m = self._get_meta()
        m[key] = value
        self._update_meta(m)

    def is_archived(self):
        m = self.get_meta_value("archived")
        if m is not None and m == "true":
            return True
        return False

    def set_archived(self, archived):
        if archived:
            self.set_meta_value("archived", "true")
        else:
            self.set_meta_value("archived", "false")

    def can_archive(self):
        ft = self.dataset.get_file_type(self.type)
        if ft is not None:
            return ft["CAN_ARCHIVE"] if "CAN_ARCHIVE" in ft else False
        return False


Dataset.files = relationship("StoredFile", order_by=StoredFile.uid, back_populates="dataset")
StoredFile.parent_id = db.Column(db.Integer, db.ForeignKey("stored_file.uid"))
StoredFile.parent = relationship(StoredFile, backref='children', remote_side=StoredFile.uid)


class TemporaryStoredFile(StoredFile):
    content = str()

    def __init__(self, content, file_name, content_type):
        self.content = content

        StoredFile.__init__(self, file_name, content_type)

    def read(self):
        return self.content

    def write(self, directory, charset='latin2'):
        self.path = os.path.join(directory, self.path)
        filesystem_helper.mkdir_directories_for(self.path)
        with open(self.path, 'wb') as f:
            content = self.read()
            if charset:
                content = content.encode(charset)
            f.write(content)

    def __repr__(self):
        return '<TemporaryStoredFile %s supposed to be written in %r (%s)>' % (self.name, self.path, self.content_type)

class ProcessingTask(db.Model):
    __tablename__ = 'processing_task'
    id = db.Column(db.Integer, primary_key=True)

    key = db.Column(db.String(128))
    storedfile_1_id = db.Column(db.Integer, db.ForeignKey("stored_file.uid"))
    storedfile_1 = relationship("StoredFile", foreign_keys=[storedfile_1_id])

    storedfile_2_id = db.Column(db.Integer, db.ForeignKey("stored_file.uid"))
    storedfile_2 = relationship("StoredFile", foreign_keys=[storedfile_2_id])
    
    status = db.Column(db.String(128))
    processing_meta = db.Column(db.String(1024))
    date_created = db.Column(db.DateTime())
    user_created_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user_created = relationship("User", foreign_keys=[user_created_id])

    date_modified = db.Column(db.DateTime())
    date_requested = db.Column(db.DateTime())

    taskdata = db.Column(db.String(8192))

    def __init__(self, name):
        self.name = name



#for _file in StoredFile.query.filter_by(token=None).all():
#    _file.token = str(uuid.uuid4()).replace("-", "")
#    print "Generated token '%s' for file '%s'" % (_file.token, _file.path)
#    db.session.add(_file)
#    db.session.commit()
