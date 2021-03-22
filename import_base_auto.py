from app import models, db
import csv
import os
import datetime

now = datetime.datetime.now()
file_path = "base_auto.csv"
if os.access(file_path, os.F_OK):
    with open(file_path, encoding='utf-8', newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for row in reader:
            start = int(row[2])
            if row[3] == "-":
                stop = now.year
            else:
                stop = int(row[3])
            for i in range(start, stop + 1):
                print(row[0], row[1], i)
                auto = models.Auto.query.all()
                if auto:
                    id_auto = auto[-1].id + 1
                else:
                    id_auto = 1
                new_auto = models.Auto(
                    id=id_auto,
                    name=row[0],
                    model=row[1],
                    year=i
                )
                db.session.add(new_auto)
                db.session.commit()

