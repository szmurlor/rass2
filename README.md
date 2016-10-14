Zależności
==========

$ sudo apt-get install unzip unrar
$ sudo apt-get install python-pip
$ sudo apt-get install gcc make python2.7-dev
$ sudo apt-get install python-vtk
$ sudo pip install virtualenv

$ cd ~
$ virtualenv venv
$ mv venv/lib/python2.7/{no,yes}-global-site-packages.txt
$ . venv/bin/activate
$ pip install flask
$ pip install flask-sqlalchemy
$ pip install uwsgi
$ pip install pydicom

$ cd rass
$ mkdir -p log
$ mkdir -p tmp/pids
$ mkdir -p tmp/sockets

$ cp config/uwsgi.ini.sample config/uwsgi.ini

Utworzenie bazy danych
==============================

* Uruchomić skrypt: python scripts/createDatabaseSchema.py
* Dodać użytkownika: python scripts/addNewUser.py

$ python
>>> from database import db
>>> db.create_all()

Wdrożenie na rass.iem.pw.edu.pl
===============================

$ ssh rass.iem.pw.edu.pl
user@rass$ sudo su -l rass
rass@rass$ cd rass
rass@rass$ git pull
<podać swoje dane do gitlab>
rass@rass$ exit
user@rass$ sudo /etc/init.d/rass stop
user@rass$ sudo /etc/init.d/rass start

Dodanie nowego użytkownika
==========================

$ ssh rass.iem.pw.edu.pl
user@rass$ sudo su -l rass
rass@rass$ cd rass
rass@rass$ python
>>> from models import User
>>> from rass import db
>>> u = User('bach')
>>> u.set_password('*******')
>>> db.session.add(u)
>>> db.session.commit()