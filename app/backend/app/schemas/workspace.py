import uuid
from datetime import datetime
from app.schemas.common import OrmModel


class WorkspaceOut(OrmModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
