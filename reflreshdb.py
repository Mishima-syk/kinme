import os
from app import db

if os.path.exists("kinme.db"):
    os.remove("kinme.db")

db.create_all()

