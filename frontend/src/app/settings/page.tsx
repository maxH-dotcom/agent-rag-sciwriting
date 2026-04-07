"use client";

import { useEffect, useState } from "react";
import { useSettingsStore, type ApiKeyStatus } from "../../../lib/stores/settings-store";
import styles from "./page.module.css";

// ── API Key row ──────────────────────────────────────────────

interface ApiKeyField {
  key: keyof ApiKeyStatus;
  label: string;
  placeholder: string;
}

const API_KEY_FIELDS: ApiKeyField[] = [
  { key: "openai", label: "OpenAI API Key", placeholder: "sk-..." },
  { key: "groq", label: "Groq API Key", placeholder: "gsk_..." },
  { key: "anthropic", label: "Anthropic API Key", placeholder: "sk-ant-..." },
  { key: "zotero", label: "Zotero API Key", placeholder: "个人密钥" },
];

function ApiKeyRow({
  field,
  status,
  onVerify,
  onSave,
}: {
  field: ApiKeyField;
  status: ApiKeyStatus[keyof ApiKeyStatus];
  onVerify: (key: keyof ApiKeyStatus, value: string) => void;
  onSave: (key: keyof ApiKeyStatus, value: string) => void;
}) {
  const [value, setValue] = useState("");
  const [visible, setVisible] = useState(false);
  const isConnected = status === "connected";
  const hasValue = value.length > 0 || isConnected;

  return (
    <div className={styles.field}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-sm)" }}>
        <label className={styles.label} style={{ marginBottom: 0 }}>{field.label}</label>
        <span className={`${styles.connectionStatus} ${styles[`connectionStatus--${status}`]}`}>
          {status === "connected" ? "已连接" : status === "error" ? "验证失败" : "未配置"}
        </span>
      </div>
      <div className={styles.apiKeyRow}>
        <div className={styles.apiKeyInput}>
          <input
            type={visible ? "text" : "password"}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={field.placeholder}
            className={styles.input}
            autoComplete="off"
            spellCheck={false}
          />
        </div>
        <button
          type="button"
          className={styles.apiKeyToggle}
          onClick={() => setVisible(!visible)}
          aria-label={visible ? "隐藏密钥" : "显示密钥"}
        >
          {visible ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
              <line x1="1" y1="1" x2="23" y2="23"/>
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          )}
        </button>
      </div>
      {hasValue && (
        <div style={{ display: "flex", gap: "var(--space-sm)", marginTop: "var(--space-sm)" }}>
          <button
            type="button"
            className={styles.testButton}
            onClick={() => onVerify(field.key, value)}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            测试连接
          </button>
          <button
            type="button"
            className={styles.testButton}
            onClick={() => onSave(field.key, value)}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
              <polyline points="17 21 17 13 7 13 7 21"/>
              <polyline points="7 3 7 8 15 8"/>
            </svg>
            保存
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────

export default function SettingsPage() {
  const {
    settings,
    apiKeyStatus,
    isLoading,
    isSaving,
    message,
    preferredModel,
    sandboxTimeout,
    autoConvertYear,
    significanceLevel,
    maxLiteratureCount,
    dataEncoding,
    allowedPackages,
    fetchSettings,
    updateSettings,
    verifyApiKey,
    setField,
    clearMessage,
  } = useSettingsStore();

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  async function handleSaveApiKey(key: keyof ApiKeyStatus, value: string) {
    if (!value) return;
    await updateSettings({ [`${key}_api_key`]: value });
  }

  async function handleVerifyApiKey(key: keyof ApiKeyStatus, value: string) {
    if (!value) return;
    await verifyApiKey(key, value);
  }

  async function handleSavePreferences() {
    await updateSettings({
      preferred_model: preferredModel,
      sandbox_timeout: sandboxTimeout,
      auto_convert_year_column: autoConvertYear,
      significance_level: significanceLevel,
      max_literature_count: maxLiteratureCount,
      data_encoding: dataEncoding,
      allowed_packages: allowedPackages.split(",").map((s) => s.trim()),
    });
  }

  if (isLoading && !settings) {
    return (
      <main className={styles.container}>
        <p style={{ color: "var(--color-text-muted)" }}>加载中...</p>
      </main>
    );
  }

  return (
    <main className={styles.container}>
      <h1 className={styles.title}>设置</h1>

      {/* ── Message ─────────────────────────── */}
      {message && (
        <div className={message.type === "success" ? styles.success : styles.error}>
          {message.text}
        </div>
      )}

      {/* ── API Key Management ─────────────── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
          </svg>
          API 密钥
        </h2>
        <p style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)", marginBottom: "var(--space-xl)" }}>
          已保存的密钥不会回显，只显示连接状态。
        </p>

        {API_KEY_FIELDS.map((field) => (
          <ApiKeyRow
            key={field.key}
            field={field}
            status={apiKeyStatus[field.key]}
            onVerify={handleVerifyApiKey}
            onSave={handleSaveApiKey}
          />
        ))}
      </section>

      {/* ── Research Preferences ────────────── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
          科研偏好
        </h2>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="preferredModel">默认分析方法</label>
          <select
            id="preferredModel"
            className={styles.select}
            value={preferredModel}
            onChange={(e) => setField("preferredModel", e.target.value)}
          >
            <option value="auto">自动选择</option>
            <option value="OLS">OLS 回归</option>
            <option value="Panel FE">面板固定效应</option>
            <option value="DID">双重差分 (DID)</option>
            <option value="STIRPAT">STIRPAT 模型</option>
            <option value="ARIMA">时间序列 (ARIMA)</option>
            <option value="XGBoost">机器学习 (XGBoost)</option>
          </select>
          <span className={styles.hint}>新建任务时的默认分析方法偏好</span>
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="significanceLevel">显著性水平</label>
          <select
            id="significanceLevel"
            className={styles.select}
            value={significanceLevel}
            onChange={(e) => setField("significanceLevel", e.target.value)}
          >
            <option value="0.01">1% (α = 0.01)</option>
            <option value="0.05">5% (α = 0.05)</option>
            <option value="0.10">10% (α = 0.10)</option>
          </select>
          <span className={styles.hint}>假设检验的显著性水平阈值</span>
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="maxLiteratureCount">最大文献数量</label>
          <input
            id="maxLiteratureCount"
            type="number"
            className={styles.input}
            value={maxLiteratureCount}
            onChange={(e) => setField("maxLiteratureCount", Number(e.target.value))}
            min={1}
            max={100}
          />
          <span className={styles.hint}>文献综述阶段最多引用的文献数量</span>
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="dataEncoding">数据编码</label>
          <select
            id="dataEncoding"
            className={styles.select}
            value={dataEncoding}
            onChange={(e) => setField("dataEncoding", e.target.value)}
          >
            <option value="UTF-8">UTF-8</option>
            <option value="GBK">GBK</option>
            <option value="Latin-1">Latin-1</option>
          </select>
          <span className={styles.hint}>读取数据文件时的默认字符编码</span>
        </div>

        <div className={styles.field}>
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={autoConvertYear}
              onChange={(e) => setField("autoConvertYear", e.target.checked)}
            />
            自动转换年份列类型
          </label>
          <span className={styles.hint}>自动将 "2020" 等字符串年份转换为整数</span>
        </div>
      </section>

      {/* ── Sandbox Config ─────────────────── */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          沙箱配置
        </h2>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="sandboxTimeout">代码执行超时 (秒)</label>
          <input
            id="sandboxTimeout"
            type="number"
            className={styles.input}
            value={sandboxTimeout}
            onChange={(e) => setField("sandboxTimeout", Number(e.target.value))}
            min={10}
            max={300}
          />
          <span className={styles.hint}>代码在沙箱中执行的最大等待时间</span>
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="allowedPackages">允许的 Python 包</label>
          <input
            id="allowedPackages"
            type="text"
            className={styles.input}
            value={allowedPackages}
            onChange={(e) => setField("allowedPackages", e.target.value)}
            placeholder="pandas, numpy, scipy, statsmodels"
          />
          <span className={styles.hint}>沙箱中允许导入的包，逗号分隔</span>
        </div>

        {settings?.sandbox_config && (
          <div className={styles.field}>
            <label className={styles.label}>最大输出</label>
            <span style={{ color: "var(--color-text-primary)", fontSize: "0.875rem" }}>
              {((settings.sandbox_config.max_output_size || 1000000) / 1024 / 1024).toFixed(1)} MB
            </span>
          </div>
        )}
      </section>

      {/* ── Available Models ────────────────── */}
      {(settings?.available_models?.length ?? 0) > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>可用模型</h2>
          <div className={styles.modelList}>
            {settings?.available_models.map((model) => (
              <span key={model} className={styles.modelTag}>{model}</span>
            ))}
          </div>
        </section>
      )}

      {/* ── Save button ─────────────────────── */}
      <button
        className={styles.saveButton}
        onClick={handleSavePreferences}
        disabled={isSaving}
      >
        {isSaving ? (
          <>
            <span style={{ display: "inline-block", width: "16px", height: "16px", border: "2px solid currentColor", borderRightColor: "transparent", borderRadius: "50%", animation: "spin 0.7s linear infinite" }} />
            保存中...
          </>
        ) : (
          <>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
              <polyline points="17 21 17 13 7 13 7 21"/>
              <polyline points="7 3 7 8 15 8"/>
            </svg>
            保存所有设置
          </>
        )}
      </button>
    </main>
  );
}
