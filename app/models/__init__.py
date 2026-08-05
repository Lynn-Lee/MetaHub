"""Import model modules so SQLAlchemy metadata is populated."""

from app.models import metadata as metadata_models

__all__ = ["metadata_models"]
