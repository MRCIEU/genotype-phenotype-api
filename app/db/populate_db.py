import csv
from app.database import SessionLocal, Base, engine, Item

# Create tables
Base.metadata.create_all(bind=engine)

def populate_db_from_csv(csv_file_path):
    db = SessionLocal()
    try:
        with open(csv_file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                item = Item(name=row['name'], description=row['description'])
                db.add(item)
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python populate_db.py <path_to_csv>")
    else:
        populate_db_from_csv(sys.argv[1])