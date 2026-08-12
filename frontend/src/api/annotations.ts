import { apiRequest } from "@/api/client";

// 字段标注接口，契约见后端 app/schemas/annotations.py。
// 注意：PUT 为整体替换 upsert，未提供的业务字段会被置空，
// 因此行内只改 business_meaning 时必须先读取现有标注再合并回填。
export interface FieldAnnotationPayload {
  business_meaning: string;
  domain_id?: number | null;
  logical_type_override?: string | null;
  dict_id?: number | null;
  dict_inline?: Record<string, unknown>[] | null;
  sample_value?: string | null;
  source_desc?: string | null;
  usage_note?: string | null;
  owner_id?: number | null;
}

export interface FieldAnnotationOut {
  urn: string;
  business_meaning: string | null;
  domain_id: number | null;
  logical_type_override: string | null;
  dict_id: number | null;
  dict_inline: Record<string, unknown>[] | null;
  sample_value: string | null;
  source_desc: string | null;
  usage_note: string | null;
  owner_id: number | null;
}

// 用现有标注（可能为空）叠加新的业务含义，构造整体替换 payload。
export function mergeAnnotationPayload(
  existing: FieldAnnotationOut | null,
  businessMeaning: string,
): FieldAnnotationPayload {
  return {
    business_meaning: businessMeaning,
    domain_id: existing?.domain_id ?? null,
    logical_type_override: existing?.logical_type_override ?? null,
    dict_id: existing?.dict_id ?? null,
    dict_inline: existing?.dict_inline ?? null,
    sample_value: existing?.sample_value ?? null,
    source_desc: existing?.source_desc ?? null,
    usage_note: existing?.usage_note ?? null,
    owner_id: existing?.owner_id ?? null,
  };
}

export function getFieldAnnotation(urn: string): Promise<FieldAnnotationOut> {
  return apiRequest<FieldAnnotationOut>("/annotations/field", { params: { urn } });
}

export function upsertFieldAnnotation(
  urn: string,
  payload: FieldAnnotationPayload,
): Promise<FieldAnnotationOut> {
  return apiRequest<FieldAnnotationOut>("/annotations/field", {
    method: "PUT",
    params: { urn },
    body: payload,
  });
}
