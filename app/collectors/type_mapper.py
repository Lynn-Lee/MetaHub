import re

_TYPE_NAME_RE = re.compile(r"^[a-zA-Z ]+")

_BASE_TYPE_MAP: dict[str, dict[str, str]] = {
    "mysql": {
        "varchar": "STRING",
        "char": "STRING",
        "text": "STRING",
        "longtext": "STRING",
        "int": "INT",
        "bigint": "INT",
        "smallint": "INT",
        "tinyint": "INT",
        "mediumint": "INT",
        "decimal": "DECIMAL",
        "numeric": "DECIMAL",
        "float": "FLOAT",
        "double": "FLOAT",
        "datetime": "DATETIME",
        "timestamp": "DATETIME",
        "date": "DATE",
        "time": "TIME",
        "json": "JSON",
        "blob": "BINARY",
        "binary": "BINARY",
        "varbinary": "BINARY",
    },
    "postgresql": {
        "varchar": "STRING",
        "character varying": "STRING",
        "text": "STRING",
        "integer": "INT",
        "bigint": "INT",
        "smallint": "INT",
        "numeric": "DECIMAL",
        "decimal": "DECIMAL",
        "money": "DECIMAL",
        "real": "FLOAT",
        "double precision": "FLOAT",
        "timestamp": "DATETIME",
        "timestamp with time zone": "DATETIME",
        "timestamp without time zone": "DATETIME",
        "timestamptz": "DATETIME",
        "date": "DATE",
        "time": "TIME",
        "boolean": "BOOL",
        "json": "JSON",
        "jsonb": "JSON",
        "bytea": "BINARY",
    },
    "oracle": {
        "varchar2": "STRING",
        "char": "STRING",
        "clob": "STRING",
        "nvarchar2": "STRING",
        "binary_float": "FLOAT",
        "binary_double": "FLOAT",
        "date": "DATETIME",
        "timestamp": "DATETIME",
        "blob": "BINARY",
        "raw": "BINARY",
    },
    "sqlserver": {
        "varchar": "STRING",
        "nvarchar": "STRING",
        "char": "STRING",
        "text": "STRING",
        "int": "INT",
        "bigint": "INT",
        "smallint": "INT",
        "tinyint": "INT",
        "decimal": "DECIMAL",
        "numeric": "DECIMAL",
        "money": "DECIMAL",
        "float": "FLOAT",
        "real": "FLOAT",
        "datetime": "DATETIME",
        "datetime2": "DATETIME",
        "smalldatetime": "DATETIME",
        "date": "DATE",
        "time": "TIME",
        "bit": "BOOL",
        "varbinary": "BINARY",
        "image": "BINARY",
    },
}


def normalize_column_type(db_type: str, raw_type: str) -> str:
    normalized_db_type = db_type.lower().strip()
    normalized_raw_type = " ".join(raw_type.lower().strip().split())

    if normalized_db_type == "mysql" and normalized_raw_type.startswith("tinyint(1"):
        return "BOOL"
    if normalized_db_type == "oracle" and normalized_raw_type.startswith("number"):
        return _normalize_oracle_number(normalized_raw_type)

    type_name = _extract_type_name(normalized_raw_type)
    return _BASE_TYPE_MAP.get(normalized_db_type, {}).get(type_name, "UNKNOWN")


def _extract_type_name(raw_type: str) -> str:
    match = _TYPE_NAME_RE.match(raw_type)
    if match is None:
        return raw_type
    return match.group(0).strip()


def _normalize_oracle_number(raw_type: str) -> str:
    numbers = [int(part) for part in re.findall(r"\d+", raw_type)]
    if numbers == [1]:
        return "BOOL"
    if len(numbers) >= 2 and numbers[1] == 0:
        return "INT"
    if len(numbers) >= 2:
        return "DECIMAL"
    return "DECIMAL"
