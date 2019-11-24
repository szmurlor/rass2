Zależności
==========

Hasła użytkowników:
coi: COI+PW+PAN
szmurlor: wld

```
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
```

Utworzenie bazy danych
==============================

* Uruchomić skrypt: python scripts/createDatabaseSchema.py
* Dodać użytkownika: python scripts/addNewUser.py

```
$ python
>>> from database import db
>>> db.create_all()
```

Wdrożenie na rass.iem.pw.edu.pl
===============================

```
$ ssh rass.iem.pw.edu.pl
user@rass$ sudo su -l rass
rass@rass$ cd rass
rass@rass$ git pull
<podać swoje dane do gitlab>
rass@rass$ exit
user@rass$ sudo /etc/init.d/rass stop
user@rass$ sudo /etc/init.d/rass start
```

Dodanie nowego użytkownika
==========================

```
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
```

Notatki związane z serwerem produkcyjnym
========================================

Obecnie (24.11.2019) RASS 2 działa na systemie Ubuntu 16.04 LTS.
Aplikacja działa na serwerze Nginx przy wykorzystaniu modułu uwsgi.
System został upgradowany i rass działa pod wersją Python 3.6.9.

Aby uzyskać wersję Pythona 3.6.9 podUbuntu 16.04 konieczne było wykonanie
kilku kroków administracyjnych:

1. Zainstalowana została alternatywna wersja Pythona 3 przy 
    wykorzystaniu instrukcji ze strony: http://ubuntuhandbook.org/index.php/2017/07/install-python-3-6-1-in-ubuntu-16-04-lts/
```
sudo add-apt-repository ppa:jonathonf/python-3.6
sudo apt-get update
sudo apt-get install python3.6
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.5 1
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 2
sudo update-alternatives --config python3
```
2. Potem uaktualniono `pip` oraz zainstlowane przy jego użyciu nową wersję `python3-pydicom`
```
python3 -m pip install python3-pydicom
```
3. Potem trzeba było zaktualizować moduł uwsgi tak aby używal Python 3.6 
   (domyślnie) w Ubuntu 16.04 uzywany jest Python 3.5.
   Wykonano procedurę opisaną pod adresem: https://www.paulox.net/2017/04/04/how-to-use-uwsgi-with-python3-6-in-ubuntu/
```
  106  sudo apt install python3.6-dev
  107  sudo apt install uwsgi
  108  sudo apt install uwsgi-src
  109  sudo apt install uuid-dev
  110  sudo apt install libcap-dev
  111  sudo apt install libpcre3-dev
  112  python3
  113  python36
  114  python3
  115  export PYTHON=python3
  116  uwsgi --build-plugin "/usr/src/uwsgi/plugins/python python36"
  117  sudo apt install openssl-dev
  118  sudo apt install libssl-dev
  119  uwsgi --build-plugin "/usr/src/uwsgi/plugins/python python36"
  120  ls
  121  sudo mv python36_plugin.so /usr/lib/uwsgi/plugins/
  122  sudo chmod 644 /usr/lib/uwsgi/plugins/python36_plugin.so
```
    W skrócie co trzeba było zrobić na podstawie strony:
```
$ sudo apt install \
python3.6 python3.6-dev uwsgi uwsgi-src uuid-dev libcap-dev libpcre3-dev
$ cd ~
$ export PYTHON=python3.6
$ uwsgi --build-plugin "/usr/src/uwsgi/plugins/python python36"
$ sudo mv python36_plugin.so /usr/lib/uwsgi/plugins/python36_plugin.so
$ sudo chmod 644 /usr/lib/uwsgi/plugins/python36_plugin.so
```