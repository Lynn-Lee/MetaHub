import { apiRequest } from "@/api/client";

// 全文检索接口，契约见后端 app/schemas/metadata_queries.py::SearchOut。
export interface TableHit {
  urn: string;
  source_id: number;
  db_name: string;
  table_name: string;
  table_type: string;
  table_comment: string | null;
  row_count: number | null;
  data_size: number | null;
  dw_layer: string | null;
  is_deleted: boolean;
  score: number | null;
}

export interface ColumnHit {
  urn: string;
  table_urn: string;
  source_id: number | null;
  db_name: string | null;
  table_name: string | null;
  column_name: string;
  ordinal: number;
  raw_type: string;
  logical_type: string;
  raw_comment: string | null;
  is_nullable: boolean;
  is_primary_key: boolean;
  is_deleted: boolean;
  business_meaning: string | null;
  effective_type: string | null;
  effective_domain_id: number | null;
  domain_name: string | null;
  score: number | null;
}

export interface FieldSearchGroup {
  table_urn: string;
  source_id: number;
  db_name: string;
  table_name: string;
  max_score: number;
  columns: ColumnHit[];
}

export interface SearchResult {
  query: string;
  total: number;
  page: number;
  page_size: number;
  tables: TableHit[];
  field_groups: FieldSearchGroup[];
}

export function search(q: string, page: number, pageSize: number): Promise<SearchResult> {
  return apiRequest<SearchResult>("/search", {
    params: { q, page, page_size: pageSize },
  });
}
