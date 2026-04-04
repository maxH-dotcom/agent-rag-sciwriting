import Link from "next/link";

export default function HomePage() {
  return (
    <main style={{ maxWidth: 980, margin: "0 auto", padding: "48px 24px" }}>
      <section style={{ background: "linear-gradient(135deg, #ffffff, #eef4ff)", borderRadius: 24, padding: 32, boxShadow: "0 12px 40px rgba(15, 23, 42, 0.08)" }}>
        <p style={{ color: "#2563eb", fontWeight: 700, margin: 0 }}>智能科研助手</p>
        <h1 style={{ fontSize: 42, lineHeight: 1.1, margin: "12px 0 16px" }}>把科研流程拆成可审核、可中断、可维护的产品。</h1>
        <p style={{ fontSize: 18, lineHeight: 1.7, maxWidth: 720 }}>
          第一版先把最关键的链路做稳：数据映射、文献证据、创新判断、代码方案、Research Brief 和草稿输出。
        </p>
        <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
          <Link href="/workspace" style={{ background: "#111827", color: "#fff", padding: "12px 18px", borderRadius: 999, textDecoration: "none" }}>
            进入工作台
          </Link>
        </div>
      </section>
    </main>
  );
}

