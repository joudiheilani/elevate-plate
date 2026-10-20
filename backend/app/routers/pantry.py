from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PantryItem
from ..schemas import PantryItemIn, PantryItemOut
from ..services.matching import normalize

router = APIRouter(prefix="/api/pantry", tags=["pantry"])
DbSession = Annotated[Session, Depends(get_db)]


def get_item_or_404(db: Session, item_id: int) -> PantryItem:
    item = db.get(PantryItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Pantry item not found")
    return item


@router.get("", response_model=list[PantryItemOut])
def list_pantry(db: DbSession):
    items = db.scalars(select(PantryItem)).all()
    return sorted(items, key=lambda item: item.name.lower())


@router.post("", response_model=PantryItemOut, status_code=status.HTTP_201_CREATED)
def add_pantry_item(payload: PantryItemIn, db: DbSession):
    """Add an item. If the same item (name and unit) is already stocked, quantities are summed."""
    existing = next(
        (
            item
            for item in db.scalars(select(PantryItem))
            if normalize(item.name) == normalize(payload.name)
            and normalize(item.unit) == normalize(payload.unit)
        ),
        None,
    )
    if existing is None:
        existing = PantryItem(**payload.model_dump())
        db.add(existing)
    elif existing.quantity is not None and payload.quantity is not None:
        existing.quantity = round(existing.quantity + payload.quantity, 2)
    db.commit()
    db.refresh(existing)
    return existing


@router.put("/{item_id}", response_model=PantryItemOut)
def update_pantry_item(item_id: int, payload: PantryItemIn, db: DbSession):
    item = get_item_or_404(db, item_id)
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_pantry_item(item_id: int, db: DbSession):
    db.delete(get_item_or_404(db, item_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
