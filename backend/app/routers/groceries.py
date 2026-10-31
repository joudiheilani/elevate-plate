from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from ..deps import CurrentUser, DbSession
from ..models import GroceryItem
from ..schemas import GroceryItemIn, GroceryItemOut

router = APIRouter(prefix="/api/groceries", tags=["custom groceries"])


@router.get("", response_model=list[GroceryItemOut])
def list_groceries(db: DbSession, user: CurrentUser):
    return db.scalars(
        select(GroceryItem).where(GroceryItem.user_id == user.id).order_by(GroceryItem.id)
    ).all()


@router.post("", response_model=GroceryItemOut, status_code=status.HTTP_201_CREATED)
def add_grocery(payload: GroceryItemIn, db: DbSession, user: CurrentUser):
    item = GroceryItem(user_id=user.id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_grocery(item_id: int, db: DbSession, user: CurrentUser):
    item = db.get(GroceryItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Grocery item not found")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
