"""
Import every model module here so Base.metadata is fully populated —
Alembic's autogenerate (and any create_all fallback) reads this to know
about every table. Add new model modules to this list as they're built
in later phases.
"""
from app.auth import models as auth_models  # noqa: F401
from app.students import models as students_models  # noqa: F401
from app.curriculum import models as curriculum_models  # noqa: F401
from app.questions import models as questions_models  # noqa: F401
from app.students import attempt_models as attempt_models  # noqa: F401
from app.evidence import models as evidence_models  # noqa: F401
from app.learning_dna import models as learning_dna_models  # noqa: F401
from app.diagnostics import models as diagnostics_models  # noqa: F401
