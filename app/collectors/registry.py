from app.collectors.base import BaseCollector, DataSourceConfig

_COLLECTORS: dict[str, type[BaseCollector]] = {}


def register_collector(db_type: str, collector_cls: type[BaseCollector]) -> None:
    _COLLECTORS[_normalize_db_type(db_type)] = collector_cls


def get_collector(db_type: str, config: DataSourceConfig) -> BaseCollector:
    normalized_db_type = _normalize_db_type(db_type)
    collector_cls = _COLLECTORS.get(normalized_db_type)
    if collector_cls is None:
        raise KeyError(f"未注册采集器: {normalized_db_type}")
    return collector_cls(config)


def _normalize_db_type(db_type: str) -> str:
    return db_type.lower().strip()
