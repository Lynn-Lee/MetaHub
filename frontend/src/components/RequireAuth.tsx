import { Spin } from "antd";
import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuthStore } from "@/stores/auth";

// 路由守卫：未登录跳登录页；会话状态确定前显示加载态，避免闪一下再跳。
export default function RequireAuth({ children }: { children: ReactNode }) {
  const status = useAuthStore((state) => state.status);

  if (status === "idle" || status === "loading") {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (status === "unauthenticated") {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
