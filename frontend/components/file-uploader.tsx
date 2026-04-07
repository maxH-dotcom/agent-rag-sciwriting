"use client";

import { useState, useRef, useCallback } from "react";
import styles from "./file-uploader.module.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const ACCEPTED_TYPES = [".csv", ".xlsx", ".xls", ".pdf", ".txt", ".md"];
const ACCEPTED_MIMES = [
  "text/csv",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
  "application/pdf",
  "text/plain",
  "text/markdown",
];

interface UploadedFile {
  name: string;
  path: string;
  size: number;
}

interface FileUploaderProps {
  onFilePath: (path: string) => void;
  accept?: string;
  label?: string;
}

interface UploadState {
  uploading: boolean;
  progress: number;
  error: string | null;
}

export function FileUploader({
  onFilePath,
  accept = ACCEPTED_TYPES.join(","),
  label = "拖拽文件到此处，或点击选择",
}: FileUploaderProps) {
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [uploadState, setUploadState] = useState<UploadState>({
    uploading: false,
    progress: 0,
    error: null,
  });
  const inputRef = useRef<HTMLInputElement>(null);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  const uploadFile = useCallback(async (file: File) => {
    setUploadState({ uploading: true, progress: 0, error: null });

    try {
      const formData = new FormData();
      formData.append("file", file);

      // Use XMLHttpRequest for progress tracking
      const result = await new Promise<{ file_path: string }>((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable) {
            setUploadState((s) => ({ ...s, progress: Math.round((e.loaded / e.total) * 100) }));
          }
        });

        xhr.addEventListener("load", () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              resolve(JSON.parse(xhr.responseText));
            } catch {
              reject(new Error("服务器响应格式错误"));
            }
          } else {
            try {
              const err = JSON.parse(xhr.responseText);
              reject(new Error(err.detail?.message || err.detail?.guidance || `上传失败 (${xhr.status})`));
            } catch {
              reject(new Error(`上传失败 (${xhr.status})`));
            }
          }
        });

        xhr.addEventListener("error", () => reject(new Error("网络错误")));
        xhr.addEventListener("abort", () => reject(new Error("上传已取消")));

        xhr.open("POST", `${API_BASE_URL}/upload`);
        xhr.send(formData);
      });

      const uploaded: UploadedFile = {
        name: file.name,
        path: result.file_path,
        size: file.size,
      };
      setUploadedFiles((prev) => [...prev, uploaded]);
      onFilePath(result.file_path);
      setUploadState({ uploading: false, progress: 100, error: null });
    } catch (err) {
      setUploadState({
        uploading: false,
        progress: 0,
        error: err instanceof Error ? err.message : "上传失败",
      });
    }
  }, [onFilePath]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!ACCEPTED_TYPES.includes(ext)) {
        setUploadState({ uploading: false, progress: 0, error: `不支持的文件类型：${ext}` });
        return;
      }
      uploadFile(file);
    }
  }, [uploadFile]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  }, [uploadFile]);

  const handleRemove = (path: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f.path !== path));
  };

  return (
    <div className={styles.container}>
      {/* Dropzone */}
      <div
        className={`${styles.dropzone} ${dragActive ? styles.dropzoneActive : ""} ${uploadState.error ? styles.dropzoneError : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !uploadState.uploading && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label={label}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleChange}
          className={styles.hiddenInput}
          aria-hidden="true"
        />

        <div className={styles.dropzoneIcon}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>

        <p className={styles.dropzoneText}>
          <strong>{label}</strong>
        </p>
        <p className={styles.dropzoneHint}>
          支持 {ACCEPTED_TYPES.join("、")} 格式
        </p>
      </div>

      {/* Upload progress */}
      {uploadState.uploading && (
        <div className={styles.progressContainer}>
          <div className={styles.progressBar}>
            <div className={styles.progressFill} style={{ width: `${uploadState.progress}%` }} />
          </div>
          <p className={styles.progressText}>上传中... {uploadState.progress}%</p>
        </div>
      )}

      {/* Error */}
      {uploadState.error && (
        <div className={styles.error} role="alert">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {uploadState.error}
        </div>
      )}

      {/* Uploaded files list */}
      {uploadedFiles.length > 0 && (
        <div className={styles.fileList}>
          {uploadedFiles.map((file) => (
            <div key={file.path} className={styles.fileItem}>
              <div className={styles.fileIcon}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
              </div>
              <div className={styles.fileInfo}>
                <p className={styles.fileName}>{file.name}</p>
                <p className={styles.fileMeta}>{formatSize(file.size)} · {file.path}</p>
              </div>
              <button
                className={styles.fileRemove}
                onClick={() => handleRemove(file.path)}
                aria-label={`移除文件 ${file.name}`}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
