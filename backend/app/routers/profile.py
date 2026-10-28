from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Profile
from ..schemas import ProfileData

router = APIRouter(prefix="/api/profile", tags=["profile & budget"])
DbSession = Annotated[Session, Depends(get_db)]

PROFILE_ID = 1


def get_profile(db: Session) -> Profile:
    """The app's single profile row, created with defaults on first use."""
    profile = db.get(Profile, PROFILE_ID)
    if profile is None:
        defaults = ProfileData()
        profile = Profile(id=PROFILE_ID, **_to_columns(defaults))
        db.add(profile)
        db.commit()
    return profile


def _to_columns(data: ProfileData) -> dict:
    return {**data.model_dump(exclude={"meals"}), "meals": ",".join(data.meals)}


def to_profile_data(profile: Profile) -> ProfileData:
    return ProfileData(
        weekly_budget=profile.weekly_budget,
        people=profile.people,
        max_minutes=profile.max_minutes,
        diet=profile.diet,
        meals=[meal for meal in profile.meals.split(",") if meal],
        mode=profile.mode,
        assume_staples=profile.assume_staples,
    )


@router.get("", response_model=ProfileData)
def read_profile(db: DbSession):
    return to_profile_data(get_profile(db))


@router.put("", response_model=ProfileData)
def update_profile(payload: ProfileData, db: DbSession):
    profile = get_profile(db)
    for field, value in _to_columns(payload).items():
        setattr(profile, field, value)
    db.commit()
    return to_profile_data(profile)
