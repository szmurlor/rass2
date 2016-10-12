import sys, os
sys.path.append(os.getcwd())

from database import db
db.create_all()
