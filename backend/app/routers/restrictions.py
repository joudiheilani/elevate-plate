from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select

from ..deps import CurrentUser, DbSession
from ..models import FoodRestriction
from ..schemas import RestrictionIn, RestrictionOut

router = APIRouter(prefix="/api/restrictions", tags=["allergies & dislikes"])


@router.get("", response_model=list[RestrictionOut])
def list_restrictions(db: DbSession, user: CurrentUser):
    return db.scalars(
        select(FoodRestriction)
        .where(FoodRestriction.user_id == user.id)
        .order_by(FoodRestriction.kind, func.lower(FoodRestriction.name))
    ).all()


@router.post("", response_model=RestrictionOut, status_code=status.HTTP_201_CREATED)
def add_restriction(payload: RestrictionIn, db: DbSession, user: CurrentUser):
    duplicate = db.scalar(
        select(FoodRestriction).where(
            FoodRestriction.user_id == user.id,
            func.lower(FoodRestriction.name) == payload.name.lower(),
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail=f'"{duplicate.name}" is already on your list')
    restriction = FoodRestriction(user_id=user.id, **payload.model_dump())
    db.add(restriction)
    db.commit()
    db.refresh(restriction)
    return restriction


@router.delete("/{restriction_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_restriction(restriction_id: int, db: DbSession, user: CurrentUser):
    restriction = db.get(FoodRestriction, restriction_id)
    if restriction is None or restriction.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(restriction)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
