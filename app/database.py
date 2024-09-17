import json
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.declarative import declared_attr
from app.settings import DATABASE_URL, SCHEMA_PATH

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Load schema from JSON file
with open(SCHEMA_PATH) as f:
    schema = json.load(f)

# Dynamically create models based on schema
class DynamicModel(Base):
    __abstract__ = True

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

for table_name, table_info in schema["tables"].items():
    attrs = {}
    for column_name, column_info in table_info["columns"].items():
        column_type = globals()[column_info["type"]]
        column_args = {}
        if "primary_key" in column_info:
            column_args["primary_key"] = column_info["primary_key"]
        if "index" in column_info:
            column_args["index"] = column_info["index"]
        attrs[column_name] = Column(column_type, **column_args)
    model = type(table_name.capitalize(), (DynamicModel,), attrs)
    globals()[model.__name__] = model

# Create tables
Base.metadata.create_all(bind=engine)