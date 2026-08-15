import { SearchOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Card,
  Input,
  List,
  Pagination,
  Space,
  Tabs,
  Tag,
  Typography,
} from "antd";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, LoadingState } from "@/components/QueryStates";
import { search, type ColumnHit, type FieldSearchGroup, type TableHit } from "@/api/search";

const PAGE_SIZE = 20;
const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 300;

// 高亮命中词：大小写不敏感，转义正则元字符（中文本身无大小写，latin 关键词兼容）。
function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function Highlight({ text, keyword }: { text: string | null | undefined; keyword: string }) {
  if (!text) {
    return null;
  }
  const kw = keyword.trim();
  if (!kw) {
    return <>{text}</>;
  }
  const parts = text.split(new RegExp(`(${escapeRegExp(kw)})`, "gi"));
  const lower = kw.toLowerCase();
  return (
    <>
      {parts.map((part, index) =>
        part.toLowerCase() === lower ? (
          <mark key={index}>{part}</mark>
        ) : (
          <span key={index}>{part}</span>
        ),
      )}
    </>
  );
}

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

function TableHitItem({ hit, keyword }: { hit: TableHit; keyword: string }) {
  return (
    <List.Item>
      <List.Item.Meta
        title={
          <Space size="small" wrap>
            <Link to={`/tables/${encodeURIComponent(hit.urn)}`}>
              <Typography.Text strong>
                <Highlight text={hit.table_name} keyword={keyword} />
              </Typography.Text>
            </Link>
            <Tag>{hit.table_type}</Tag>
            {hit.dw_layer && <Tag color="blue">{hit.dw_layer}</Tag>}
          </Space>
        }
        description={
          <Space direction="vertical" size={2}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {hit.db_name} · {hit.urn}
            </Typography.Text>
            {hit.table_comment && (
              <Typography.Text>
                <Highlight text={hit.table_comment} keyword={keyword} />
              </Typography.Text>
            )}
          </Space>
        }
      />
      {hit.score != null && <Tag color="geekblue">score {hit.score.toFixed(2)}</Tag>}
    </List.Item>
  );
}

function ColumnHitItem({ hit, keyword }: { hit: ColumnHit; keyword: string }) {
  const comment = hit.business_meaning ?? hit.raw_comment;
  return (
    <List.Item>
      <List.Item.Meta
        title={
          <Space size="small" wrap>
            <Typography.Text strong>
              <Highlight text={hit.column_name} keyword={keyword} />
            </Typography.Text>
            <Tag>{hit.effective_type ?? hit.raw_type}</Tag>
            {hit.is_primary_key && <Tag color="gold">PK</Tag>}
            {hit.domain_name && <Tag color="purple">{hit.domain_name}</Tag>}
          </Space>
        }
        description={
          comment && (
            <Typography.Text>
              <Highlight text={comment} keyword={keyword} />
            </Typography.Text>
          )
        }
      />
      {hit.score != null && <Tag color="geekblue">score {hit.score.toFixed(2)}</Tag>}
    </List.Item>
  );
}

function FieldGroupCard({ group, keyword }: { group: FieldSearchGroup; keyword: string }) {
  return (
    <Card
      size="small"
      style={{ marginBottom: 12 }}
      title={
        <Space size="small" wrap>
          <Link to={`/tables/${encodeURIComponent(group.table_urn)}`}>
            <Typography.Text strong>{group.table_name}</Typography.Text>
          </Link>
          <Typography.Text type="secondary" style={{ fontSize: 12, fontWeight: 400 }}>
            {group.db_name} · {group.table_urn}
          </Typography.Text>
        </Space>
      }
    >
      <List
        dataSource={group.columns}
        renderItem={(column) => (
          <ColumnHitItem key={column.urn} hit={column} keyword={keyword} />
        )}
      />
    </Card>
  );
}

export default function SearchPage() {
  const [input, setInput] = useState("");
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState<"tables" | "fields">("tables");

  const debouncedInput = useDebouncedValue(input, DEBOUNCE_MS);
  const keyword = debouncedInput.trim();
  const enabled = keyword.length >= MIN_QUERY_LENGTH;

  // 查询词变化时回到第一页。
  useEffect(() => {
    setPage(1);
  }, [keyword]);

  const query = useQuery({
    queryKey: ["search", keyword, page],
    queryFn: () => search(keyword, page, PAGE_SIZE),
    enabled,
    placeholderData: (previous) => previous,
  });

  const data = query.data;
  const columnCount = useMemo(
    () => data?.field_groups.reduce((sum, group) => sum + group.columns.length, 0) ?? 0,
    [data],
  );

  const renderResults = () => {
    // 空态之一：查询词不足。
    if (!enabled) {
      return <EmptyState description={`请输入至少 ${MIN_QUERY_LENGTH} 个字符开始搜索`} />;
    }
    // 加载态。
    if (query.isLoading) {
      return <LoadingState />;
    }
    // 错误态 / 无权限态。
    if (query.isError) {
      return (
        <ErrorState
          error={query.error}
          onRetry={() => void query.refetch()}
          forbiddenMessage="无权限访问搜索"
          errorMessage="搜索失败"
        />
      );
    }
    if (!data) {
      return null;
    }
    // 空结果态。
    if (data.total === 0) {
      return <EmptyState simple={false} description={`未找到与「${keyword}」匹配的结果`} />;
    }

    return (
      <>
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as "tables" | "fields")}
          items={[
            {
              key: "tables",
              label: `表 (${data.tables.length})`,
              children:
                data.tables.length > 0 ? (
                  <List
                    dataSource={data.tables}
                    renderItem={(hit) => (
                      <TableHitItem key={hit.urn} hit={hit} keyword={keyword} />
                    )}
                  />
                ) : (
                  <EmptyState description="本页无表命中" />
                ),
            },
            {
              key: "fields",
              label: `字段 (${columnCount})`,
              children:
                data.field_groups.length > 0 ? (
                  data.field_groups.map((group) => (
                    <FieldGroupCard key={group.table_urn} group={group} keyword={keyword} />
                  ))
                ) : (
                  <EmptyState description="本页无字段命中" />
                ),
            },
          ]}
        />
        <div style={{ textAlign: "right", marginTop: 8 }}>
          <Pagination
            current={data.page}
            pageSize={data.page_size}
            total={data.total}
            showSizeChanger={false}
            onChange={setPage}
          />
        </div>
      </>
    );
  };

  return (
    <Card>
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <Input
          size="large"
          allowClear
          autoFocus
          prefix={<SearchOutlined />}
          placeholder="搜索表名、字段名、注释或业务语义…"
          value={input}
          onChange={(event) => setInput(event.target.value)}
        />
        {renderResults()}
      </Space>
    </Card>
  );
}
