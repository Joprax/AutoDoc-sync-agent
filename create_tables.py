# create_tables.py
from app.db.base import Base, engine
import app.db.models  # ensures all model classes register with Base before create_all

Base.metadata.create_all(bind=engine)
print("Tables created.")