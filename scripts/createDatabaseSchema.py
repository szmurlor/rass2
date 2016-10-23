# coding=utf-8
import sys, os
import json
import database

sys.path.append(os.getcwd())

from database import db
db.drop_all()
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
         "formats": "Archiwum zip z plikami DICOM",
         "only_one": True,
         "parent_type": None,
         "order": 10},
        {"name": "roi",
         "desc": "Dane o strukturach ROI",
         "formats": "Pojedynczy plik DICOM, lub archiwum zip z plikiem",
         "only_one": True,
         "parent_type": None,
         "order": 20},
        {"name": "rt",
         "desc": "Plany RT",
         "formats": "Archiwum zip z plikami DICOM",
         "only_one": False,
         "parent_type": None,
         "order": 30},
        {"name": "beamlets",
         "desc": "Dane do optymalizacji",
         "formats": "Archiwum zip z plikami przetworzonymi do optymalizacji (obliczone dawki z podziałem na beamlety)",
         "only_one": False,
         "parent_type": "rt",
         "order": 40},
        {"name": "pareto",
         "desc": "Wyniki pareto",
         "formats": "Archiwum zip z wynikami Pareto",
         "only_one": False,
         "parent_type": "rt",
         "order": 50},
        {"name": "fluences",
         "desc": "Mapy fluencji po optymalizacji",
         "formats": "Archiwum z fluencjami poszczególnych wiązek uzyskane z optymalizacji",
         "only_one": False,
         "parent_type": "rt",
         "order": 60}
    ]
}
sftypes = json.dumps(file_types, indent=True)
dt.file_types = sftypes
db.session.add(dt)
db.session.commit()

