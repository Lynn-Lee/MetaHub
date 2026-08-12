import { ArrowLeftOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import { getTable, getTableDdl, listColumns, type ColumnMeta } from "@/api/tables";

const PAGE_SIZE = 50;

// data_size 后端以字节计，转人类可读。
function formatBytes(value: number | null): string {
  if (value == null) {
    return "—";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  const units = ["KB", "MB", "GB", "TB"];
  let size = value / 1024;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(1)} ${units[unit]}`;
}

function formatCount(value: number | null): string {
  return value == null ? "—" : value.toLocaleString();
}

// 长文本单元格：截断 + Tooltip，避免撑破固定列宽。
function EllipsisCell({ text }: { text: string | null }) {
  if (!text) {
    return <Typography.Text type="secondary">—</Typography.Text>;
  }
  return (
    <Tooltip title={text} placement="topLeft">
      <Typography.Text ellipsis style={{ maxWidth: "100%" }}>
        {text}
      </Typography.Text>
    </Tooltip>
  );
}

const COLUMN_DEFS: ColumnsType<ColumnMeta> = [
  {
    title: "#",
    dataIndex: "ordinal",
    key: "ordinal",
    width: 60,
    fixed: "left",
  },
  {
    title: "字段名",
    dataIndex: "column_name",
    key: "column_name",
    width: 200,
    fixed: "left",
    render: (name: string, record) => (
      <Space size={4} wrap>
        <Typography.Text strong>{name}</Typography.Text>
        {record.is_primary_key && <Tag color="gold">PK</Tag>}
      </Space>
    ),
  },
  {
    title: "类型",
    dataIndex: "raw_type",
    key: "type",
    width: 150,
    render: (rawType: string, record) => (
      <Tooltip title={`采集类型：${rawType}`} placement="topLeft">
        <Tag>{record.effective_type ?? rawType}</Tag>
      </Tooltip>
    ),
  },
  {
    title: "可空",
    dataIndex: "is_nullable",
    key: "is_nullable",
    width: 80,
    render: (nullable: boolean) =>
      nullable ? <Tag>可空</Tag> : <Tag color="blue">非空</Tag>,
  },
  {
    title: "业务含义",
    key: "meaning",
    width: 280,
    render: (_, record) => <EllipsisCell text={record.business_meaning ?? record.raw_comment} />,
  },
  {
    title: "数据域",
    dataIndex: "domain_name",
    key: "domain_name",
    width: 140,
    render: (domain: string | null) =>
      domain ? <Tag color="purple">{domain}</Tag> : <Typography.Text type="secondary">—</Typography.Text>,
  },
];

function ColumnsTab({ tableUrn }: { tableUrn: string }) {
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["columns", tableUrn, page],
    queryFn: () => listColumns(tableUrn, page, PAGE_SIZE),
    placeholderData: (previous) => previous,
  });

  if (query.isError) {
    return (
      <Alert
        type="error"
        showIcon
        message="字段加载失败"
        description={query.error instanceof Error ? query.error.message : "请稍后重试"}
        action={
          <Button size="small" onClick={() => void query.refetch()}>
            重试
          </Button>
        }
      />
    );
  }

  return (
    <Table<ColumnMeta>
      rowKey="urn"
      size="middle"
      loading={query.isLoading}
      columns={COLUMN_DEFS}
      dataSource={query.data?.items ?? []}
      tableLayout="fixed"
      scroll={{ x: 910 }}
      pagination={{
        current: query.data?.page ?? page,
        pageSize: query.data?.page_size ?? PAGE_SIZE,
        total: query.data?.total ?? 0,
        showSizeChanger: false,
        hideOnSinglePage: true,
        onChange: setPage,
      }}
    />
  );
}

function DdlTab({ tableUrn, active }: { tableUrn: string; active: boolean }) {
  const query = useQuery({
    queryKey: ["ddl", tableUrn],
    queryFn: () => getTableDdl(tableUrn),
    enabled: active,
  });

  if (query.isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "48px 0" }}>
        <Spin />
      </div>
    );
  }
  if (query.isError) {
    return (
      <Alert
        type="error"
        showIcon
        message="DDL 生成失败"
        description={query.error instanceof Error ? query.error.message : "请稍后重试"}
        action={
          <Button size="small" onClick={() => void query.refetch()}>
            重试
          </Button>
        }
      />
    );
  }
  if (!query.data) {
    return null;
  }

  return (
    <Typography.Paragraph
      copyable={{ text: query.data.ddl }}
      style={{
        margin: 0,
        padding: 16,
        background: "#f6f8fa",
        borderRadius: 6,
        fontFamily: "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace",
        fontSize: 13,
        whiteSpace: "pre",
        overflowX: "auto",
      }}
    >
      {query.data.ddl}
    </Typography.Paragraph>
  );
}

export default function TableDetailPage() {
  const { urn = "" } = useParams();
  const [activeTab, setActiveTab] = useState<"columns" | "ddl">("columns");

  const tableQuery = useQuery({
    queryKey: ["table", urn],
    queryFn: () => getTable(urn),
    enabled: urn.length > 0,
  });

  if (tableQuery.isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "64px 0" }}>
        <Spin size="large" />
      </div>
    );
  }

  const table = tableQuery.data?.items[0];

  // 错误态 / 不存在态：403 无权限，其余含空 items 归为“表不存在”。
  if (tableQuery.isError || !table) {
    const err = tableQuery.error;
    const isForbidden = err instanceof ApiError && err.status === 403;
    return (
      <Card>
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <Link to="/search">
            <Button icon={<ArrowLeftOutlined />}>返回搜索</Button>
          </Link>
          {isForbidden ? (
            <Alert type="warning" showIcon message="无权限访问该表" />
          ) : tableQuery.isError ? (
            <Alert
              type="error"
              showIcon
              message="加载失败"
              description={err instanceof Error ? err.message : "请稍后重试"}
              action={
                <Button size="small" onClick={() => void tableQuery.refetch()}>
                  重试
                </Button>
              }
            />
          ) : (
            <Empty description={`未找到表「${urn}」`} />
          )}
        </Space>
      </Card>
    );
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <Link to="/search">
        <Button icon={<ArrowLeftOutlined />}>返回搜索</Button>
      </Link>
      <Card>
        <Descriptions
          title={
            <Space size="small" wrap>
              <Typography.Text strong style={{ fontSize: 18 }}>
                {table.table_name}
              </Typography.Text>
              <Tag>{table.table_type}</Tag>
              {table.dw_layer && <Tag color="blue">{table.dw_layer}</Tag>}
              {table.is_deleted && <Tag color="red">已删除</Tag>}
            </Space>
          }
          column={{ xs: 1, sm: 2, md: 3 }}
          size="small"
          bordered
        >
          <Descriptions.Item label="库名">{table.db_name}</Descriptions.Item>
          <Descriptions.Item label="行数">{formatCount(table.row_count)}</Descriptions.Item>
          <Descriptions.Item label="大小">{formatBytes(table.data_size)}</Descriptions.Item>
          <Descriptions.Item label="URN" span={3}>
            <Typography.Text copyable code>
              {table.urn}
            </Typography.Text>
          </Descriptions.Item>
          <Descriptions.Item label="表注释" span={3}>
            {table.table_comment ?? <Typography.Text type="secondary">—</Typography.Text>}
          </Descriptions.Item>
        </Descriptions>
      </Card>
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as "columns" | "ddl")}
          items={[
            {
              key: "columns",
              label: "字段",
              children: <ColumnsTab tableUrn={table.urn} />,
            },
            {
              key: "ddl",
              label: "DDL",
              children: <DdlTab tableUrn={table.urn} active={activeTab === "ddl"} />,
            },
          ]}
        />
      </Card>
    </Space>
  );
}
