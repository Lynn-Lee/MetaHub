"""Import model modules so SQLAlchemy metadata is populated."""

from app.models import knowledge as knowledge_models
from app.models import metadata as metadata_models
from app.models import support as support_models

__all__ = ["knowledge_models", "metadata_models", "support_models"]
