import sys, os
sys.path.append(os.getcwd())

from sys import argv
from getpass import getpass
from database import db, User

if __name__ == '__main__':
  if len(argv) == 2:
    u = User(argv[1])
    print "Creating user %s" % u.username
    p = getpass()
    u.set_password(p)
    db.session.add(u)
    db.session.commit()
  else:
    print "Usage:\tpython %s username" % ( argv[0] )

