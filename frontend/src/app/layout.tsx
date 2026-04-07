import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "智能科研工作助手",
  description: "把科研流程拆成可审核、可中断、可维护的产品",
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🔬</text></svg>",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
