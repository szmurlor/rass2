# coding=utf-8
import sys, os
import json
import database

sys.path.append(os.getcwd())

from database import db

dt = database.DatasetType.query.filter_by(id=1).one()
file_types = {"types": [
  {
   "name": "ct",
   "parent_type": None,
   "formats": "Archiwum zip z plikami DICOM rozpoczynającymi się od znaków CT. Można wgrać tylko jeden plik z zestawem danych CT.",
   "desc": "Dane CT",
   "order": 10,
   "only_one": True,
   "responsible": "COI",
   "allowed_extensions": "*.zip"
  },
  {
   "name": "roi",
   "parent_type": None,
   "formats": "Pojedynczy plik DICOM, lub archiwum zip z plikiem. Nazwa pliku DICOM zaczyna się od znaków RS. Można wgrać tylko jeden plik.",
   "desc": "Dane o strukturach ROI",
   "order": 20,
   "only_one": True,
   "responsible": "COI",
   "allowed_extensions": "*.zip|RS*.dcm"
  },
  {
   "name": "rt",
   "parent_type": None,
   "formats": "Archiwum zip z plikami DICOM o nazwie zaczynającej się od znaków RP. Można wgrać wiele różnych planów.",
   "desc": "Plany radioterapii",
   "order": 30,
   "only_one": False,
   "responsible": "COI",
   "allowed_extensions": "*.zip|RP*.dcm"
  },
  {
   "name": "beamlets",
   "parent_type": "rt",
   "formats": "Archiwum zip z plikami przetworzonymi do optymalizacji (obliczone dawki z podziałem na beamlety)",
   "desc": "Dane do optymalizacji",
   "order": 40,
   "only_one": False,
   "responsible": "PW",
   "allowed_extensions": "*.zip|x_*.txt"
  },
  {
   "name": "optdesc",
   "parent_type": "rt",
   "formats": "Arkusz Excel",
   "desc": "Opis optymalizacji",
   "order": 45,
   "only_one": True,
   "responsible": "COI",
   "allowed_extensions": "*.xls|*.xlsx"
  },
  {
   "name": "pareto",
   "parent_type": "rt",
   "formats": "Archiwum zip z wynikami Pareto",
   "desc": "Wyniki pareto",
   "order": 50,
   "only_one": False,
   "responsible": "PAN",
   "allowed_extensions": "*.zip"
  },
  {
   "name": "fluences",
   "parent_type": "pareto",
   "formats": "Archiwum zip z fluencjami poszczególnych wiązek uzyskane z optymalizacji",
   "desc": "Mapy fluencji po optymalizacji",
   "order": 60,
   "only_one": True,
   "responsible": "PW",
   "allowed_extensions": "*.zip"
  },
  {
   "name": "other",
   "parent_type": None,
   "formats": "Dowolne pliki",
   "desc": "Inne",
   "order": 70,
   "only_one": True,
   "responsible": "Wszyscy",
   "allowed_extensions": "*"
  }
 ]
}
sftypes = json.dumps(file_types, indent=True)
dt.file_types = sftypes
db.session.add(dt)
db.session.commit()

