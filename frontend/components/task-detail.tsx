"use client";

import { useState } from "react";
import type { TaskPayload } from "../lib/api";
import styles from "./task-detail.module.css";

// ── Result type guards ───────────────────────────────────────

interface DataMappingResult {
  type: "data_mapping";
  mappings: { source: string; target: string; dtype: string; description?: string }[];
}

interface LiteratureReviewResult {
  type: "literature_review";
  papers: {
    title: string;
    authors?: string[];
    year?: number;
    journal?: string;
    citations?: number;
    abstract?: string;
    doi?: string;
  }[];
}

interface CodeGenerationResult {
  type: "code_generation";
  language: string;
  code: string;
  description?: string;
  output?: string;
}

interface ResearchBriefResult {
  type: "research_brief";
  content: string; // Markdown
  title?: string;
}

type ParsedResult =
  | DataMappingResult
  | LiteratureReviewResult
  | CodeGenerationResult
  | ResearchBriefResult
  | { type: "unknown"; data: unknown };

function parseResult(result: Record<string, unknown> | null): ParsedResult {
  if (!result) return { type: "unknown", data: null };

  if (result.type === "data_mapping" && Array.isArray(result.mappings)) {
    return result as unknown as DataMappingResult;
  }
  if (result.type === "literature_review" && Array.isArray(result.papers)) {
    return result as unknown as LiteratureReviewResult;
  }
  if (result.type === "code_generation" && typeof result.code === "string") {
    return result as unknown as CodeGenerationResult;
  }
  if (result.type === "research_brief" && typeof result.content === "string") {
    return result as unknown as ResearchBriefResult;
  }

  return { type: "unknown", data: result };
}

// ── Sub-renderers ────────────────────────────────────────────

function DataMappingView({ mappings }: { mappings: DataMappingResult["mappings"] }) {
  if (!mappings.length) {
    return <div className={styles.empty}>暂无映射数据</div>;
  }
  return (
    <table className={styles.dataTable}>
      <thead>
        <tr>
          <th>源变量</th>
          <th>目标变量</th>
          <th>类型</th>
          <th>描述</th>
        </tr>
      </thead>
      <tbody>
        {mappings.map((m, i) => (
          <tr key={i}>
            <td><code>{m.source}</code></td>
            <td><code>{m.target}</code></td>
            <td><span style={{ textTransform: "capitalize" }}>{m.dtype}</span></td>
            <td>{m.description || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function LiteratureReviewView({ papers }: { papers: LiteratureReviewResult["papers"] }) {
  if (!papers.length) {
    return <div className={styles.empty}>暂无文献数据</div>;
  }
  return (
    <div className={styles.litGrid}>
      {papers.map((paper, i) => (
        <div key={i} className={styles.litCard}>
          <h3 className={styles.litTitle}>{paper.title}</h3>
          <div className={styles.litMeta}>
            {paper.year && <span className={styles.litBadge}>{paper.year}</span>}
            {paper.journal && <span className={styles.litBadge}>{paper.journal}</span>}
            {paper.citations !== undefined && (
              <span className={`${styles.litBadge} ${styles.litBadgeHighlight}`}>
                被引 {paper.citations}
              </span>
            )}
          </div>
          {paper.abstract && <p className={styles.litAbstract}>{paper.abstract}</p>}
          {paper.authors?.length && (
            <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginTop: "var(--space-sm)" }}>
              {paper.authors.join(", ")}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function CodeGenerationView({ result }: { result: CodeGenerationResult }) {
  return (
    <div className={styles.codeBlock}>
      <div className={styles.codeToolbar}>
        <span className={styles.codeLang}>{result.language || "python"}</span>
        {result.description && (
          <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
            {result.description}
          </span>
        )}
      </div>
      <pre className={styles.codeContent}>{result.code}</pre>
      {result.output && (
        <div style={{ borderTop: "1px solid var(--color-border)", padding: "var(--space-md)" }}>
          <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--color-text-muted)", marginBottom: "var(--space-sm)", textTransform: "uppercase" }}>输出</p>
          <pre style={{ fontSize: "0.8125rem", fontFamily: "monospace", color: "var(--color-text-secondary)", whiteSpace: "pre-wrap", margin: 0 }}>{result.output}</pre>
        </div>
      )}
    </div>
  );
}

function MarkdownView({ content, title }: { content: string; title?: string }) {
  // Very simple markdown renderer — renders key block elements
  // For production, consider a library like react-markdown
  const paragraphs = content.split(/\n\n+/);

  return (
    <div className={styles.markdown}>
      {title && <h1>{title}</h1>}
      {paragraphs.map((block, i) => {
        if (block.startsWith("# ")) return <h1 key={i}>{block.slice(2)}</h1>;
        if (block.startsWith("## ")) return <h2 key={i}>{block.slice(3)}</h2>;
        if (block.startsWith("### ")) return <h3 key={i}>{block.slice(4)}</h3>;
        if (block.startsWith("- ") || block.startsWith("* ")) {
          const items = block.split(/\n/).filter(Boolean);
          return (
            <ul key={i}>
              {items.map((item, j) => <li key={j}>{item.replace(/^[-*]\s+/, "")}</li>)}
            </ul>
          );
        }
        if (/^\d+\.\s/.test(block)) {
          const items = block.split(/\n/).filter(Boolean);
          return (
            <ol key={i}>
              {items.map((item, j) => <li key={j}>{item.replace(/^\d+\.\s+/, "")}</li>)}
            </ol>
          );
        }
        if (block.startsWith("> ")) return <blockquote key={i}>{block.slice(2)}</blockquote>;
        // Inline code and bold
        const processed = block
          .replace(/`([^`]+)`/g, "<code>$1</code>")
          .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        return <p key={i} dangerouslySetInnerHTML={{ __html: processed }} />;
      })}
    </div>
  );
}

function UnknownView({ data }: { data: unknown }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <div style={{ padding: "var(--space-md) var(--space-lg)", color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
        未知结果类型，使用原始 JSON 展示
      </div>
      <button
        className={styles.jsonToggle}
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
        {expanded ? "收起" : "展开"} 原始 JSON
      </button>
      {expanded && (
        <div className={styles.jsonContent}>
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
    </>
  );
}

// ── Main component ───────────────────────────────────────────

interface TaskDetailProps {
  task: TaskPayload;
}

export function TaskDetail({ task }: TaskDetailProps) {
  const [activeTab, setActiveTab] = useState<string>("result");

  const parsed = parseResult(task.result ?? null);

  // Determine available tabs
  const availableTabs: { id: string; label: string; icon: JSX.Element }[] = [
    {
      id: "result",
      label: "结果",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
      ),
    },
  ];

  if (task.interrupt_data) {
    availableTabs.push({
      id: "interrupt",
      label: "中断数据",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      ),
    });
  }

  return (
    <div className={styles.container}>
      {/* Tab bar */}
      <div className={styles.tabBar} role="tablist">
        {availableTabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`${styles.tab} ${activeTab === tab.id ? styles.tabActive : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Result section */}
      {activeTab === "result" && (
        <div className={styles.section} role="tabpanel">
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              {parsed.type === "data_mapping" ? "数据映射结果"
               : parsed.type === "literature_review" ? "文献综述结果"
               : parsed.type === "code_generation" ? "代码生成结果"
               : parsed.type === "research_brief" ? "研究简报"
               : "任务结果"}
            </h2>
          </div>
          <div className={styles.sectionBody}>
            {parsed.type === "data_mapping" && (
              <DataMappingView mappings={parsed.mappings} />
            )}
            {parsed.type === "literature_review" && (
              <LiteratureReviewView papers={parsed.papers} />
            )}
            {parsed.type === "code_generation" && (
              <CodeGenerationView result={parsed} />
            )}
            {parsed.type === "research_brief" && (
              <MarkdownView content={parsed.content} title={parsed.title} />
            )}
            {parsed.type === "unknown" && (
              <UnknownView data={parsed.data} />
            )}
          </div>
        </div>
      )}

      {/* Interrupt data section */}
      {activeTab === "interrupt" && task.interrupt_data && (
        <div className={styles.section} role="tabpanel">
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              中断数据
            </h2>
            {task.interrupt_reason && (
              <span style={{ fontSize: "0.8125rem", color: "var(--color-warning)" }}>
                {task.interrupt_reason}
              </span>
            )}
          </div>
          <div className={styles.sectionBody}>
            <pre className={styles.codeContent} style={{ margin: 0 }}>
              {JSON.stringify(task.interrupt_data, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
