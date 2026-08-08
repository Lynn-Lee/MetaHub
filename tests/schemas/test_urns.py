import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.urns import ColumnUrn, TableUrn


def test_table_urn_accepts_standard_four_part_identifier() -> None:
    assert TypeAdapter(TableUrn).validate_python("mysql:crm:sales:orders") == (
        "mysql:crm:sales:orders"
    )


def test_column_urn_accepts_standard_five_part_identifier() -> None:
    assert TypeAdapter(ColumnUrn).validate_python("mysql:crm:sales:orders:pay_amount") == (
        "mysql:crm:sales:orders:pay_amount"
    )


@pytest.mark.parametrize(
    "urn",
    [
        "mysql:crm:sales",
        "mysql:crm:sales:orders:",
        "mysql:crm:sales:orders/pay_amount",
        "mysql:crm:sales:Orders:pay_amount",
        "mysql:crm:sales:orders:pay amount",
    ],
)
def test_column_urn_rejects_non_standard_values(urn: str) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(ColumnUrn).validate_python(urn)
