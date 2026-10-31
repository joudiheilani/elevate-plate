from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import CurrentUser, DbSession
from ..models import PantryItem, User
from ..schemas import PantryItemIn, PantryItemOut
from ..services.matching import normalize

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


def get_item_or_404(db: Session, user: User, item_id: int) -> PantryItem:
    item = db.get(PantryItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Pantry item not found")
    return item


def _pantry(db: Session, user: User):
    return db.scalars(select(PantryItem).where(PantryItem.user_id == user.id))


@router.get("", response_model=list[PantryItemOut])
def list_pantry(db: DbSession, user: CurrentUser):
    return sorted(_pantry(db, user), key=lambda item: item.name.lower())


@router.post("", response_model=PantryItemOut, status_code=status.HTTP_201_CREATED)
def add_pantry_item(payload: PantryItemIn, db: DbSession, user: CurrentUser):
    """Add an item. If the same item (name and unit) is already stocked, quantities are summed."""
    existing = next(
        (
            item
            for item in _pantry(db, user)
            if normalize(item.name) == normalize(payload.name)
            and normalize(item.unit) == normalize(payload.unit)
        ),
        None,
    )
    if existing is None:
        existing = PantryItem(user_id=user.id, **payload.model_dump())
        db.add(existing)
    elif existing.quantity is not None and payload.quantity is not None:
        existing.quantity = round(existing.quantity + payload.quantity, 2)
    db.commit()
    db.refresh(existing)
    return existing


@router.put("/{item_id}", response_model=PantryItemOut)
def update_pantry_item(item_id: int, payload: PantryItemIn, db: DbSession, user: CurrentUser):
    item = get_item_or_404(db, user, item_id)
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_pantry_item(item_id: int, db: DbSession, user: CurrentUser):
    db.delete(get_item_or_404(db, user, item_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
