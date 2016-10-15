import sys, os
import json
import database

sys.path.append(os.getcwd())

from database import db
# db.drop_all()
db.create_all()

u = database.User('szmurlor')
u.set_password('wld')
db.session.add(u)
db.session.commit()

dt = database.DatasetType('CT / ROI Structures / RT Plan / Pareto results')
file_types = {
    "types": [
        {"name": "ct",
         "desc": "Dane CT",
         "formats": "Archiwum zip z plikami DICOM"},
        {"name": "roi",
         "desc": "Dane o strukturach ROI",
         "formats": "Pojedynczy plik DICOM, lub archiwum zip z plikiem"},
        {"name": "rt",
         "desc": "Plany RT",
         "formats": "Archiwum zip z plikami DICOM"},
        {"name": "pareto",
         "desc": "Wyniki pareto",
         "formats": "Archiwum zip z wynikami Pareto, lub pojedyncze pliki z wynikami"}
    ]
}
sftypes = json.dumps(file_types, indent=True)
dt.file_types = sftypes
db.session.add(dt)
db.session.commit()

