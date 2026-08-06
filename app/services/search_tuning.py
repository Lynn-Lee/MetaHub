"""检索阈值调优指标（DEV-TASKS T4.2）。"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True, slots=True)
class SearchQueryCase:
    query: str
    category: str
    expected_urns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ThresholdMeasurement:
    threshold: float
    recall: float
    p95_ms: float
    avg_result_count: float


@dataclass(frozen=True, slots=True)
class RepresentativeFixture:
    tables: list[dict[str, object]]
    columns: list[dict[str, object]]
    annotations: list[dict[str, object]]


def build_v01_query_cases() -> list[SearchQueryCase]:
    """V0.1 代表性查询词集。

    真库接入后应保留分类比例，并把 expected_urns 替换成真实核心库字段。
    """
    return [
        SearchQueryCase("订单", "zh_2", ("mysql:crm:sales:orders:order_no",)),
        SearchQueryCase("支付", "zh_2", ("mysql:crm:sales:orders:pay_amount",)),
        SearchQueryCase("用户", "zh_2", ("mysql:crm:user_center:users:user_id",)),
        SearchQueryCase("手机", "zh_2", ("mysql:crm:user_center:users:mobile",)),
        SearchQueryCase("状态", "zh_2", ("mysql:crm:sales:orders:order_status",)),
        SearchQueryCase("结算", "zh_2", ("mysql:crm:sales:settlements:settle_status",)),
        SearchQueryCase("退款", "zh_2", ("mysql:crm:sales:refunds:refund_status",)),
        SearchQueryCase("实名", "zh_2", ("mysql:crm:user_center:user_auth:auth_status",)),
        SearchQueryCase("地址", "zh_2", ("mysql:crm:logistics:shipments:receiver_address",)),
        SearchQueryCase("发票", "zh_2", ("mysql:crm:finance:invoices:invoice_status",)),
        SearchQueryCase("订单金额", "zh_4", ("mysql:crm:sales:orders:pay_amount",)),
        SearchQueryCase("创建时间", "zh_4", ("mysql:crm:sales:orders:created_at",)),
        SearchQueryCase("实名认证", "zh_4", ("mysql:crm:user_center:user_auth:auth_status",)),
        SearchQueryCase("物流单号", "zh_4", ("mysql:crm:logistics:shipments:tracking_no",)),
        SearchQueryCase("收货地址", "zh_4", ("mysql:crm:logistics:shipments:receiver_address",)),
        SearchQueryCase("结算状态", "zh_4", ("mysql:crm:sales:settlements:settle_status",)),
        SearchQueryCase("支付渠道", "zh_4", ("mysql:crm:sales:payments:pay_channel",)),
        SearchQueryCase("用户等级", "zh_4", ("mysql:crm:user_center:users:user_level",)),
        SearchQueryCase("退款原因", "zh_4", ("mysql:crm:sales:refunds:refund_reason",)),
        SearchQueryCase("发票抬头", "zh_4", ("mysql:crm:finance:invoices:invoice_title",)),
        SearchQueryCase("order_no", "english", ("mysql:crm:sales:orders:order_no",)),
        SearchQueryCase("pay_amount", "english", ("mysql:crm:sales:orders:pay_amount",)),
        SearchQueryCase("user_id", "english", ("mysql:crm:user_center:users:user_id",)),
        SearchQueryCase("mobile", "english", ("mysql:crm:user_center:users:mobile",)),
        SearchQueryCase("auth_status", "english", ("mysql:crm:user_center:user_auth:auth_status",)),
        SearchQueryCase("tracking_no", "english", ("mysql:crm:logistics:shipments:tracking_no",)),
        SearchQueryCase("refund_reason", "english", ("mysql:crm:sales:refunds:refund_reason",)),
        SearchQueryCase("invoice_title", "english", ("mysql:crm:finance:invoices:invoice_title",)),
        SearchQueryCase("订单 order", "mixed", ("mysql:crm:sales:orders:order_no",)),
        SearchQueryCase("支付 amount", "mixed", ("mysql:crm:sales:orders:pay_amount",)),
        SearchQueryCase("用户 mobile", "mixed", ("mysql:crm:user_center:users:mobile",)),
        SearchQueryCase("实名 auth", "mixed", ("mysql:crm:user_center:user_auth:auth_status",)),
        SearchQueryCase("物流 tracking", "mixed", ("mysql:crm:logistics:shipments:tracking_no",)),
        SearchQueryCase("退款 refund", "mixed", ("mysql:crm:sales:refunds:refund_status",)),
        SearchQueryCase("发票 invoice", "mixed", ("mysql:crm:finance:invoices:invoice_status",)),
        SearchQueryCase("结算 settle", "mixed", ("mysql:crm:sales:settlements:settle_status",)),
    ]


def build_representative_fixture() -> RepresentativeFixture:
    source_id = 910001
    table_specs = [
        ("sales", "orders", "订单主表"),
        ("sales", "payments", "支付流水表"),
        ("sales", "refunds", "退款申请表"),
        ("sales", "settlements", "结算单表"),
        ("user_center", "users", "用户基础信息表"),
        ("user_center", "user_auth", "用户实名认证表"),
        ("logistics", "shipments", "物流发货表"),
        ("finance", "invoices", "发票信息表"),
    ]
    column_specs = [
        ("sales", "orders", "order_no", "varchar(64)", "STRING", "订单编号", "订单唯一编号"),
        ("sales", "orders", "pay_amount", "decimal(12,2)", "DECIMAL", "支付金额", "订单支付金额"),
        ("sales", "orders", "order_status", "tinyint", "INT", "订单状态", "订单履约状态"),
        ("sales", "orders", "created_at", "datetime", "DATETIME", "创建时间", "订单创建时间"),
        ("sales", "payments", "pay_channel", "varchar(32)", "STRING", "支付渠道", "订单支付渠道"),
        (
            "sales",
            "payments",
            "trade_no",
            "varchar(64)",
            "STRING",
            "支付流水号",
            "第三方支付流水号",
        ),
        ("sales", "refunds", "refund_status", "tinyint", "INT", "退款状态", "退款处理状态"),
        ("sales", "refunds", "refund_reason", "varchar(255)", "STRING", "退款原因", "用户退款原因"),
        ("sales", "settlements", "settle_status", "tinyint", "INT", "结算状态", "商户结算状态"),
        (
            "sales",
            "settlements",
            "settle_amount",
            "decimal(12,2)",
            "DECIMAL",
            "结算金额",
            "商户结算金额",
        ),
        ("user_center", "users", "user_id", "bigint", "INT", "用户ID", "用户唯一标识"),
        ("user_center", "users", "mobile", "varchar(20)", "STRING", "手机号", "用户手机号"),
        ("user_center", "users", "user_level", "varchar(16)", "STRING", "用户等级", "用户会员等级"),
        (
            "user_center",
            "user_auth",
            "auth_status",
            "tinyint",
            "INT",
            "认证状态",
            "用户实名认证状态",
        ),
        (
            "user_center",
            "user_auth",
            "id_card_no",
            "varchar(32)",
            "STRING",
            "身份证号",
            "实名证件号",
        ),
        (
            "logistics",
            "shipments",
            "tracking_no",
            "varchar(64)",
            "STRING",
            "物流单号",
            "物流运单号",
        ),
        (
            "logistics",
            "shipments",
            "receiver_address",
            "varchar(255)",
            "STRING",
            "收货地址",
            "收货人地址",
        ),
        ("finance", "invoices", "invoice_status", "tinyint", "INT", "发票状态", "发票开具状态"),
        (
            "finance",
            "invoices",
            "invoice_title",
            "varchar(128)",
            "STRING",
            "发票抬头",
            "发票抬头名称",
        ),
    ]
    tables: list[dict[str, object]] = [
        {
            "urn": _table_urn(db_name, table_name),
            "source_id": source_id,
            "db_name": db_name,
            "table_name": table_name,
            "table_type": "TABLE",
            "table_comment": comment,
            "is_deleted": False,
        }
        for db_name, table_name, comment in table_specs
    ]
    columns: list[dict[str, object]] = [
        {
            "urn": _column_urn(db_name, table_name, column_name),
            "table_urn": _table_urn(db_name, table_name),
            "source_id": source_id,
            "db_name": db_name,
            "table_name": table_name,
            "column_name": column_name,
            "raw_type": raw_type,
            "logical_type": logical_type,
            "raw_comment": raw_comment,
            "is_deleted": False,
        }
        for db_name, table_name, column_name, raw_type, logical_type, raw_comment, _ in column_specs
    ]
    annotations: list[dict[str, object]] = [
        {
            "urn": _column_urn(db_name, table_name, column_name),
            "asset_type": "COLUMN",
            "business_meaning": business_meaning,
            "usage_note": raw_comment,
            "source_desc": "",
            "status": "CONFIRMED",
            "source_type": "MANUAL",
        }
        for db_name, table_name, column_name, _, _, raw_comment, business_meaning in column_specs
    ]
    return RepresentativeFixture(tables=tables, columns=columns, annotations=annotations)


def calculate_recall(returned_urns: list[str], expected_urns: list[str] | tuple[str, ...]) -> float:
    expected = set(expected_urns)
    if not expected:
        return 0.0
    hits = expected.intersection(returned_urns)
    return len(hits) / len(expected)


def percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def recommend_threshold(
    measurements: list[ThresholdMeasurement],
    *,
    min_recall: float,
    max_p95_ms: float,
) -> ThresholdMeasurement:
    eligible = [
        item for item in measurements if item.recall >= min_recall and item.p95_ms <= max_p95_ms
    ]
    candidates = eligible or measurements
    return sorted(
        candidates,
        key=lambda item: (
            item.threshold,
            -item.p95_ms,
            -item.avg_result_count,
        ),
        reverse=True,
    )[0]


def _table_urn(db_name: str, table_name: str) -> str:
    return f"mysql:crm:{db_name}:{table_name}"


def _column_urn(db_name: str, table_name: str, column_name: str) -> str:
    return f"{_table_urn(db_name, table_name)}:{column_name}"
