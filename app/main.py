from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import List
from app.database import SessionLocal, Base, engine, Variants, Traits, Coloc, Finemap
from api_analytics.fastapi import Analytics
from app.settings import ANALYTICS_KEY

# Define Pydantic models
class VariantsResponse(BaseModel):
    id: int
    chr: int
    pos: int
    a1: str
    a2: str

    model_config = ConfigDict(from_attributes=True)
    
# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Analytics
analytics = Analytics(app, api_key=ANALYTICS_KEY)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/variants/", response_model=List[VariantsResponse])
def get_variants(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    variants = db.query(Variants).offset(skip).limit(limit).all()
    return variants


# @app.post("/items/", response_model=ItemResponse)
# def create_item(item: ItemCreate, db: Session = Depends(get_db)):
#     db_item = Item(**item.model_dump())
#     db.add(db_item)
#     db.commit()
#     db.refresh(db_item)
#     return db_item

# @app.get("/items/{item_id}", response_model=ItemResponse)
# def read_item(item_id: int, db: Session = Depends(get_db)):
#     db_item = db.query(Item).filter(Item.id == item_id).first()
#     if db_item is None:
#         raise HTTPException(status_code=404, detail="Item not found")
#     return db_item

# @app.get("/items/", response_model=List[ItemResponse])
# def read_items(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
#     items = db.query(Item).offset(skip).limit(limit).all()
#     return items

# @app.put("/items/{item_id}", response_model=ItemResponse)
# def update_item(item_id: int, item: ItemCreate, db: Session = Depends(get_db)):
#     db_item = db.query(Item).filter(Item.id == item_id).first()
#     if db_item is None:
#         raise HTTPException(status_code=404, detail="Item not found")
#     item_data = item.model_dump()
#     for key, value in item_data.items():
#         setattr(db_item, key, value)
#     db.commit()
#     db.refresh(db_item)
#     return db_item

# @app.delete("/items/{item_id}", response_model=ItemResponse)
# def delete_item(item_id: int, db: Session = Depends(get_db)):
#     db_item = db.query(Item).filter(Item.id == item_id).first()
#     if db_item is None:
#         raise HTTPException(status_code=404, detail="Item not found")
#     db.delete(db_item)
#     db.commit()
#     return db_item

# @app.get("/items/search/", response_model=List[ItemResponse])
# def search_items(
#     name: str = Query(..., min_length=1, description="Search query for item name"),
#     skip: int = 0,
#     limit: int = 10,
#     db: Session = Depends(get_db)
# ):
#     items = db.query(Item).filter(func.lower(Item.name).contains(func.lower(name))).offset(skip).limit(limit).all()
#     return items
