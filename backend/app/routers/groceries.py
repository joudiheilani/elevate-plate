from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import GroceryItem
from ..schemas import GroceryItemIn, GroceryItemOut

router = APIRouter(prefix="/api/groceries", tags=["custom groceries"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[GroceryItemOut])
def list_groceries(db: DbSession):
    return db.scalars(select(GroceryItem).order_by(GroceryItem.id)).all()


@router.post("", response_model=GroceryItemOut, status_code=status.HTTP_201_CREATED)
def add_grocery(payload: GroceryItemIn, db: DbSession):
    item = GroceryItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_grocery(item_id: int, db: DbSession):
    item = db.get(GroceryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Grocery item not found")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
