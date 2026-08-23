from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.students.models import StudentProfile
from app.students.dependencies import get_current_student_profile
from app.evidence.models import EvidenceEvent
from app.evidence.schemas import EvidenceEventOut

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/me", response_model=list[EvidenceEventOut])
def get_my_evidence(
    db: Session = Depends(get_db),
    student: StudentProfile = Depends(get_current_student_profile),
):
    """
    Section 10. Read-only history, scoped to the authenticated student the
    same way attempts are (student.id from the JWT-derived profile, never
    a client-supplied id). No endpoint anywhere lets a client create,
    edit, or delete an EvidenceEvent — it is a pure side effect of
    grading an attempt (see students/attempt_service.py).
    """
    return (
        db.query(EvidenceEvent)
        .filter(EvidenceEvent.student_id == student.id)
        .order_by(EvidenceEvent.timestamp.desc())
        .all()
    )
