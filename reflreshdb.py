import os
from app import db

if os.path.exists("knimea.db"):
    os.remove("knimea.db")

db.create_all()

