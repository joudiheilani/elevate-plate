import datetime as dt

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete, select

from ..deps import CurrentUser, DbSession
from ..models import DiningOut, MealPlanEntry
from ..schemas import DiningOutIn, DiningOutOut
from .plan import week_dining_stmt

router = APIRouter(prefix="/api/dining-out", tags=["dining out"])


@router.get("", response_model=list[DiningOutOut])
def list_dining_out(start: dt.date, db: DbSession, user: CurrentUser):
    """Meals eaten out in the 7 days beginning at `start`."""
    return db.scalars(week_dining_stmt(user, start).order_by(DiningOut.day)).all()


@router.put("", response_model=DiningOutOut)
def set_dining_out(payload: DiningOutIn, db: DbSession, user: CurrentUser):
    """Mark a meal slot as eaten out, replacing any recipe planned there."""
    slot = (DiningOut.user_id == user.id, DiningOut.day == payload.day)
    entry = db.scalar(select(DiningOut).where(*slot, DiningOut.meal_type == payload.meal_type))
    if entry is None:
        entry = DiningOut(user_id=user.id, day=payload.day, meal_type=payload.meal_type)
        db.add(entry)
    entry.note = payload.note
    entry.cost = payload.cost
    db.execute(
        delete(MealPlanEntry).where(
            MealPlanEntry.user_id == user.id,
            MealPlanEntry.day == payload.day,
            MealPlanEntry.meal_type == payload.meal_type,
        )
    )
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_dining_out(entry_id: int, db: DbSession, user: CurrentUser):
    entry = db.get(DiningOut, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Dining-out entry not found")
    db.delete(entry)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
