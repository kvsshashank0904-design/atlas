from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.curriculum.models import Subject, Concept
from app.curriculum.schemas import SubjectOut, ConceptOut

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(db: Session = Depends(get_db), _=Depends(get_current_user)):
    subjects = (
        db.query(Subject)
        .options(joinedload(Subject.chapters).joinedload("concepts"))
        .all()
    )
    return subjects


@router.get("/concepts/{concept_code}", response_model=ConceptOut)
def get_concept(concept_code: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """
    Returns a concept with its prerequisite codes resolved — this is the
    shape Study GPS / prerequisite rerouting (Section 20) will read from.
    """
    concept = db.query(Concept).filter(Concept.concept_code == concept_code).first()
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    out = ConceptOut.model_validate(concept)
    out.prerequisite_concept_codes = [
        link.prerequisite_concept.concept_code for link in concept.prerequisite_links
    ]
    return out
