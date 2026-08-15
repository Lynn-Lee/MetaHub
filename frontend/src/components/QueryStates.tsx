// 四态统一收口（T7.6）：加载态 / 错误态 / 无权限态 / 空态。
// 各数据页复用同一套组件，避免各处重复的居中 Spin、Alert + 重试、403→无权限分支。

import { Empty, Alert, Button, Spin } from "antd";

import { ApiError } from "@/api/client";

// 加载态：居中 Spin。padding 控制上下留白（不同页面留白不同）。
export function LoadingState({
  size = "default",
  padding = 48,
}: {
  size?: "small" | "default" | "large";
  padding?: number;
}) {
  return (
    <div style={{ textAlign: "center", padding: `${padding}px 0` }}>
      <Spin size={size} />
    </div>
  );
}

// 错误态 + 无权限态：后端 403 归为无权限（warning，无重试），其余为可重试错误。
export function ErrorState({
  error,
  onRetry,
  forbiddenMessage = "无权限访问",
  errorMessage = "加载失败",
}: {
  error: unknown;
  onRetry?: () => void;
  forbiddenMessage?: string;
  errorMessage?: string;
}) {
  const isForbidden = error instanceof ApiError && error.status === 403;
  if (isForbidden) {
    return <Alert type="warning" showIcon message={forbiddenMessage} />;
  }
  return (
    <Alert
      type="error"
      showIcon
      message={errorMessage}
      description={error instanceof Error ? error.message : "请稍后重试"}
      action={
        onRetry && (
          <Button size="small" onClick={onRetry}>
            重试
          </Button>
        )
      }
    />
  );
}

// 空态：无数据或提示。默认简约图（antd 大图仅用于整页空结果）。
export function EmptyState({
  description,
  simple = true,
}: {
  description: string;
  simple?: boolean;
}) {
  return (
    <Empty
      image={simple ? Empty.PRESENTED_IMAGE_SIMPLE : undefined}
      description={description}
    />
  );
}
