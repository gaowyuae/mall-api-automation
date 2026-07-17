from pathlib import Path

PROJECT_ROOT_MARKERS = ("pyproject.toml", ".git")


def project_root(start=None, max_depth=10):
    current_dir = Path(start or __file__).resolve()

    if current_dir.is_file():
        current_dir = current_dir.parent

    for _ in range(max_depth):
        if any((current_dir / marker).exists() for marker in PROJECT_ROOT_MARKERS):
            return current_dir
        if current_dir == current_dir.parent:
            break
        current_dir = current_dir.parent

    raise FileNotFoundError(
        "未能定位到项目根目录 (pyproject.toml or .git 不存在)."
    )


def project_path(*parts):
    return project_root() / Path(*parts)
