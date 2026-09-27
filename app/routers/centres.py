from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.centre import DiagnosticCentre, DiagnosticTest
from app.schemas.centre import (
    DiagnosticCentreCreate,
    DiagnosticCentreListItem,
    DiagnosticCentreResponse,
    DiagnosticTestCreate,
    DiagnosticTestResponse,
)

router = APIRouter(prefix="/centres", tags=["Diagnostic Centres"])


@router.get("", response_model=list[DiagnosticCentreListItem])
def list_centres(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[DiagnosticCentre]:
    return db.query(DiagnosticCentre).offset(skip).limit(limit).all()


@router.post("", response_model=DiagnosticCentreResponse, status_code=status.HTTP_201_CREATED)
def create_centre(body: DiagnosticCentreCreate, db: Session = Depends(get_db)) -> DiagnosticCentre:
    centre = DiagnosticCentre(name=body.name.strip(), location=body.location.strip())
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


@router.get("/{centre_id}", response_model=DiagnosticCentreResponse)
def get_centre(centre_id: int, db: Session = Depends(get_db)) -> DiagnosticCentre:
    centre = (
        db.query(DiagnosticCentre)
        .options(joinedload(DiagnosticCentre.tests))
        .filter(DiagnosticCentre.id == centre_id)
        .first()
    )
    if centre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre not found")
    return centre


@router.post(
    "/{centre_id}/tests",
    response_model=DiagnosticTestResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_test(
    centre_id: int,
    body: DiagnosticTestCreate,
    db: Session = Depends(get_db),
) -> DiagnosticTest:
    centre = db.get(DiagnosticCentre, centre_id)
    if centre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre not found")
    test = DiagnosticTest(
        centre_id=centre_id,
        name=body.name.strip(),
        description=body.description,
        price=body.price,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@router.get("/{centre_id}/tests", response_model=list[DiagnosticTestResponse])
def list_tests(centre_id: int, db: Session = Depends(get_db)) -> list[DiagnosticTest]:
    centre = db.get(DiagnosticCentre, centre_id)
    if centre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre not found")
    return db.query(DiagnosticTest).filter(DiagnosticTest.centre_id == centre_id).all()
