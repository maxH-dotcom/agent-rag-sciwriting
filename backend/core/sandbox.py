"""代码安全检查 + subprocess 沙箱执行."""

from __future__ import annotations

import ast
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Tuple

from backend.agents.models.code_generation import CodeCheckResult, ExecutionResult

# ---------------------------------------------------------------------------
# 1. 代码安全检查
# ---------------------------------------------------------------------------

FORBIDDEN_PATTERNS: List[Tuple[str, str]] = [
    (r"\bos\.system\b", "禁止使用 os.system"),
    (r"\bsubprocess\b", "禁止使用 subprocess"),
    (r"\beval\s*\(", "禁止使用 eval()"),
    (r"\bexec\s*\(", "禁止使用 exec()"),
    (r"\b__import__\s*\(", "禁止使用 __import__()"),
    (r"\bimport\s+os\b", "禁止导入 os 模块"),
    (r"\bimport\s+shutil\b", "禁止导入 shutil 模块"),
    (r"\bimport\s+socket\b", "禁止导入 socket 模块"),
    (r"\bimport\s+http\b", "禁止导入 http 模块"),
    (r"\bimport\s+urllib\b", "禁止导入 urllib 模块"),
    (r"\bimport\s+requests\b", "禁止导入 requests 模块"),
]

# 允许的顶级 import 白名单（模块名前缀）
ALLOWED_IMPORT_PREFIXES = {
    "pandas", "numpy", "scipy", "statsmodels", "sklearn",
    "matplotlib", "seaborn", "linearmodels",
    "math", "statistics", "collections", "itertools",
    "json", "csv", "io", "typing", "dataclasses",
    "warnings", "functools", "operator", "decimal",
    "pathlib",
}


def check_code(code: str) -> CodeCheckResult:
    """对生成的代码进行语法检查 + 安全检查."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1) 语法检查
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        errors.append(f"语法错误 (行 {exc.lineno}): {exc.msg}")
        return CodeCheckResult(passed=False, errors=errors, warnings=warnings)

    # 2) 正则安全检查
    for pattern, msg in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            errors.append(msg)

    # 3) AST import 白名单检查
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check_import(alias.name, errors)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                _check_import(node.module, errors)

    # 4) 警告：检测可能的长时间运行循环
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            warnings.append("检测到 while 循环，注意执行超时风险")

    return CodeCheckResult(passed=len(errors) == 0, errors=errors, warnings=warnings)


def _check_import(module_name: str, errors: list[str]) -> None:
    top_level = module_name.split(".")[0]
    if top_level not in ALLOWED_IMPORT_PREFIXES:
        errors.append(f"禁止导入模块: {module_name} (不在白名单中)")


# ---------------------------------------------------------------------------
# 2. Subprocess 沙箱执行
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT_S = 60
MAX_OUTPUT_BYTES = 1_000_000  # 1 MB stdout/stderr 截断


def execute_in_sandbox(
    code: str,
    data_files: list[str] | None = None,
    timeout: int = DEFAULT_TIMEOUT_S,
    python_executable: str | None = None,
) -> ExecutionResult:
    """在 subprocess 中执行 Python 代码.

    - 在临时目录中运行，隔离文件系统影响
    - 将 data_files 符号链接到临时目录，让代码可通过文件名读取
    - 带超时保护
    """
    if python_executable is None:
        python_executable = _find_python()

    t0 = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="sandbox_") as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 检查 pandas 是否可用，不可用则尝试安装
        _ensure_dependencies(python_executable, tmpdir)

        # 符号链接数据文件
        tmpdir_path = Path(tmpdir)

        # 符号链接数据文件
        if data_files:
            for fpath in data_files:
                src = Path(fpath)
                if src.exists():
                    dst = tmpdir_path / src.name
                    if not dst.exists():
                        dst.symlink_to(src.resolve())

        # 写入脚本
        script_path = tmpdir_path / "_analysis.py"
        script_path.write_text(code, encoding="utf-8")

        # 执行
        try:
            proc = subprocess.run(
                [python_executable, str(script_path)],
                cwd=str(tmpdir_path),
                capture_output=True,
                timeout=timeout,
                env=_sandbox_env(tmpdir),
            )
            elapsed = int((time.monotonic() - t0) * 1000)

            stdout = proc.stdout.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
            stderr = proc.stderr.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]

            # 收集输出文件
            output_files = _collect_output_files(tmpdir_path)

            if proc.returncode != 0:
                return ExecutionResult(
                    success=False,
                    stdout=stdout,
                    stderr=stderr,
                    error_message=f"进程退出码 {proc.returncode}",
                    execution_time_ms=elapsed,
                    output_files=output_files,
                )

            return ExecutionResult(
                success=True,
                stdout=stdout,
                stderr=stderr,
                execution_time_ms=elapsed,
                output_files=output_files,
            )

        except subprocess.TimeoutExpired:
            elapsed = int((time.monotonic() - t0) * 1000)
            return ExecutionResult(
                success=False,
                error_message=f"执行超时 ({timeout}s)",
                execution_time_ms=elapsed,
            )
        except Exception as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            return ExecutionResult(
                success=False,
                error_message=str(exc),
                execution_time_ms=elapsed,
            )


def _find_python() -> str:
    """寻找带完整依赖的 Python 解释器 (优先项目 .venv)."""
    import sys
    from pathlib import Path

    # 优先使用项目 .venv
    project_venv = Path(__file__).parent.parent.parent / ".venv" / "bin" / "python"
    if project_venv.exists():
        return str(project_venv)

    # 其次使用当前解释器
    return sys.executable


def _sandbox_env(tmpdir: str) -> dict[str, str]:
    """构建可访问 .venv 依赖的环境变量."""
    import sys
    from pathlib import Path

    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/usr/local/bin"),
        "HOME": tmpdir,
        "TMPDIR": tmpdir,
        "LANG": "en_US.UTF-8",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    # 继承 VIRTUAL_ENV 并确保 PYTHONPATH 包含 site-packages
    if venv := os.environ.get("VIRTUAL_ENV"):
        env["VIRTUAL_ENV"] = venv
        venv_path = Path(venv)
        site_packages = venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
        if site_packages.exists():
            existing_pythonpath = os.environ.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{site_packages}{os.pathsep}{existing_pythonpath}"

    return env


def _ensure_dependencies(python_executable: str, tmpdir: str) -> None:
    """检查并安装必要的依赖（pandas等）."""
    # 测试 pandas 是否可用
    test_code = "import pandas; print('pandas ok')"
    try:
        proc = subprocess.run(
            [python_executable, "-c", test_code],
            capture_output=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return  # pandas 已可用
    except Exception:
        pass

    # 不可用则尝试安装到用户目录
    try:
        subprocess.run(
            [python_executable, "-m", "pip", "install", "--quiet", "--user", "pandas", "numpy"],
            capture_output=True,
            timeout=60,
        )
    except Exception:
        pass  # 安装失败不影响后续执行


def _collect_output_files(tmpdir: Path) -> list[str]:
    """收集脚本执行后生成的输出文件 (图片/CSV)."""
    output_exts = {".png", ".jpg", ".svg", ".pdf", ".csv", ".xlsx", ".html"}
    return [
        str(p) for p in tmpdir.iterdir()
        if p.is_file() and p.suffix.lower() in output_exts and p.name != "_analysis.py"
    ]
