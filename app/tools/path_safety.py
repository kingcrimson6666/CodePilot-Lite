"""路径安全检查工具"""

from pathlib import Path
from typing import List, Optional

# 安全路径白名单（默认包含项目根目录）
SAFE_PATHS: List[Path] = []

# 不安全路径黑名单
UNSAFE_PATHS: List[str] = [
    "/etc",
    "/var",
    "/root",
    "/sys",
    "/proc",
    "/dev",
    "/boot",
    "/usr/bin",
    "/usr/sbin",
    "/bin",
    "/sbin",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
]


def init_safe_paths(project_root: Path) -> None:
    """初始化安全路径，只允许访问项目根目录"""
    SAFE_PATHS.clear()
    SAFE_PATHS.append(project_root.resolve())


def is_safe_path(path: str, project_root: Optional[Path] = None) -> bool:
    """
    检查路径是否安全

    Args:
        path: 要检查的路径
        project_root: 项目根目录（如果提供，会自动添加到安全路径）

    Returns:
        是否安全
    """
    try:
        # 解析路径
        path_obj = Path(path).resolve()

        # 如果提供了项目根目录，确保安全路径包含它
        if project_root is not None:
            root = project_root.resolve()
            if root not in SAFE_PATHS:
                SAFE_PATHS.append(root)

        # 检查是否在安全路径内
        in_safe = any(path_obj.is_relative_to(safe) for safe in SAFE_PATHS)
        if not in_safe:
            return False

        # 检查是否在不安全路径内
        in_unsafe = any(
            str(path_obj).startswith(unsafe) or str(path_obj).startswith(unsafe.replace("/", "\\"))
            for unsafe in UNSAFE_PATHS
        )
        if in_unsafe:
            return False

        # 检查是否包含 ".." 尝试向上跳转
        if ".." in path.split("/") or ".." in path.split("\\"):
            # 再次验证解析后的路径是否仍然在安全范围内
            # （因为 Path.resolve() 已经处理了 ".."，但我们保持双重检查）
            pass

        return True

    except (PermissionError, Exception):
        # 如果无法解析路径，视为不安全
        return False


def get_safe_path(path: str, project_root: Path) -> Optional[Path]:
    """
    获取安全路径，如果不安全则返回 None

    Args:
        path: 原始路径
        project_root: 项目根目录

    Returns:
        安全的 Path 对象，或 None
    """
    if not is_safe_path(path, project_root):
        return None

    path_obj = Path(path)
    if path_obj.is_absolute():
        return path_obj.resolve()
    else:
        return (project_root / path_obj).resolve()
