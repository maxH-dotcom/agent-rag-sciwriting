import type { ReactNode } from "react";

export const metadata = {
  title: "智能科研助手",
  description: "面向科研工作流的多 Agent 工作台",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body style={{ margin: 0, fontFamily: "ui-sans-serif, system-ui, sans-serif", background: "#f5f7fb", color: "#111827" }}>
        {children}
      </body>
    </html>
  );
}

