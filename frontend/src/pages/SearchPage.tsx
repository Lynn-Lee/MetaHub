import { Card, Empty, Typography } from "antd";

// T7.1 占位：全局搜索页的真实实现见 T7.3（搜索框、结果列表、高亮、表/字段 Tab）。
export default function SearchPage() {
  return (
    <Card>
      <Typography.Title level={4}>搜索</Typography.Title>
      <Empty description="搜索页将在 T7.3 实现" />
    </Card>
  );
}
