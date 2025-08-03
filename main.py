from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
import os
from dotenv import load_dotenv
from databases import Database
from sqlalchemy import Column, Integer, String, Float, Text, select
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Load .env variables into the environment
load_dotenv()
# Read the DATABASE_URL value
DATABASE_URL = os.getenv("DATABASE_URL")
# Create the async database client
database = Database(DATABASE_URL)

class ItemInDB(Base):
	__tablename__ = "items"
	id = Column(Integer, primary_key=True, index=True)
	name = Column (String(50), nullable=False)
	description = Column(Text)
	price = Column(Float, nullable=False)

app = FastAPI()

# Startup/shutdown events for database
@app.on_event("startup")
async def on_startup():
	await database.connect()

@app.on_event("shutdown")
async def on_shutdown():
	await database.disconnect()

# Defining Model
class Item(BaseModel):
	id: int
	name: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9]+$")
	description: str | None = Field(None, max_length=200)
	price: float = Field(..., gt=0)
	class Config:
		from_attributes= True
		
items: dict[int, Item] = {}

# Implementing CRUD endpoints
# Create
@app.post("/items/", response_model=Item, status_code=201)
async def create_item(item: Item):
	query = select(ItemInDB).where(ItemInDB.id == item.id)
	existing = await database.fetch_one(query)
	if existing:
		raise HTTPException(status_code=409, detail="Item already exists")

	# Insert the new row
	insert_stmt = ItemInDB.__table__.insert().values(**item.dict())
	await database.execute(insert_stmt)
	return item


# Read
@app.get("/items/{item_id}", response_model=Item)
async def read_item(item_id: int):
	query = select(ItemInDB).where(ItemInDB.id == item_id)
	row = await database.fetch_one(query)
	if not row:
		raise HTTPException(status_code=404, detail="Item not found")
	return Item.from_orm(row)


# Update
@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, updated: Item):
	# Ensure it exists
	query = select(ItemInDB).where(ItemInDB.id == item_id)
	existing = await database.fetch_one(query)
	if not existing:
		raise HTTPException(status_code=404, detail="Item not found")
	# Validate ID consistancy
	if updated.id != item_id:
		raise HTTPException(status_code=400, detail="ID mismatch")
	# Perform the update
	update_stmt = (
		ItemInDB.__table__
		.update()
		.where(ItemInDB.id == item_id)
		.values(**updated.dict())
	)

	await database.execute(update_stmt)
	return updated

# Delete
@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
	# Ensure it exists
	query = select(ItemInDB).where(ItemInDB.id == item_id)
	existing = await database.fetch_one(query)
	if not existing:
		raise HTTPException(status_code=404, detail="Item not found")

	# Delete
	delete_stmt = ItemInDB.__table__.delete().where(ItemInDB.id == item_id)
	await database.execute(delete_stmt)

# Optional, max_price filter
@app.get("/items", response_model=List[Item])
async def list_items(max_price: float | None = None):
	rows = await database.fetch_all(select(ItemInDB))
	items_list = [Item.from_orm(r) for r in rows]
	if max_price is not None:
		items_list = [i for i in items_list if i.price <= max_price]
	return items_list



@app.get('/')
def read_root():
	return {"message":"Hello, World!"}