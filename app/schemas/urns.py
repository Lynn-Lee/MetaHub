"""URN schema types（DEV-TASKS T6.1）。"""

from typing import Annotated, TypeAlias

from pydantic import StringConstraints

URN_PART_PATTERN = r"(?:[a-z0-9_.-]|\\:)+"
TABLE_URN_PATTERN = (
    rf"^{URN_PART_PATTERN}:{URN_PART_PATTERN}:{URN_PART_PATTERN}:{URN_PART_PATTERN}$"
)
COLUMN_URN_PATTERN = (
    rf"^{URN_PART_PATTERN}:{URN_PART_PATTERN}:{URN_PART_PATTERN}:"
    rf"{URN_PART_PATTERN}:{URN_PART_PATTERN}$"
)

TableUrn: TypeAlias = Annotated[
    str,
    StringConstraints(
        min_length=7,
        max_length=512,
        pattern=TABLE_URN_PATTERN,
    ),
]

ColumnUrn: TypeAlias = Annotated[
    str,
    StringConstraints(
        min_length=9,
        max_length=768,
        pattern=COLUMN_URN_PATTERN,
    ),
]
