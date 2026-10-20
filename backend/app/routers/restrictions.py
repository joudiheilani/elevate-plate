from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FoodRestriction
from ..schemas import RestrictionIn, RestrictionOut

router = APIRouter(prefix="/api/restrictions", tags=["allergies & dislikes"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[RestrictionOut])
def list_restrictions(db: DbSession):
    return db.scalars(
        select(FoodRestriction).order_by(FoodRestriction.kind, func.lower(FoodRestriction.name))
    ).all()


@router.post("", response_model=RestrictionOut, status_code=status.HTTP_201_CREATED)
def add_restriction(payload: RestrictionIn, db: DbSession):
    duplicate = db.scalar(
        select(FoodRestriction).where(func.lower(FoodRestriction.name) == payload.name.lower())
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail=f'"{duplicate.name}" is already on your list')
    restriction = FoodRestriction(**payload.model_dump())
    db.add(restriction)
    db.commit()
    db.refresh(restriction)
    return restriction


@router.delete("/{restriction_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_restriction(restriction_id: int, db: DbSession):
    restriction = db.get(FoodRestriction, restriction_id)
    if restriction is None:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(restriction)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
