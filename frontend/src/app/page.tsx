import Link from "next/link";
import styles from "./page.module.css";

export default function HomePage() {
  return (
    <main className={styles.main}>
      {/* ── Hero ─────────────────────────────────────── */}
      <section className={styles.hero}>
        <div className={styles.heroInner}>
          <span className={styles.heroBadge}>智能科研助手</span>
          <h1 className={styles.heroHeading}>
            把科研流程拆成<br />可审核、可中断、可维护的产品
          </h1>
          <p className={styles.heroDesc}>
            第一版先把最关键的链路做稳：数据映射、文献证据、创新判断、
            代码方案、Research Brief 和草稿输出。
          </p>
          <Link href="/workspace" className={styles.ctaPrimary}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
            进入工作台
          </Link>
        </div>

        {/* ── Features ─────────────────────────────────── */}
        <div className={styles.features}>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
              </svg>
            </div>
            <h3>文献检索</h3>
            <p>Zotero / OpenAlex / paper-qa 多源检索，自动提取方法、领域、地区证据</p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
              </svg>
            </div>
            <h3>代码生成</h3>
            <p>基于文献证据自动生成 OLS / Panel FE / DID / STIRPAT 分析脚本</p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
            <h3>人工审核</h3>
            <p>5 个中断点覆盖全流程，关键节点人工确认后继续执行</p>
          </div>
        </div>
      </section>
    </main>
  );
}
