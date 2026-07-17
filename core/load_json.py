import json
from pathlib import Path

from core.paths import project_root


def _candidate_paths(root_dir, filename, data_dir):
    new_base = root_dir / "testcase" / "data"
    data_dir_path = Path(data_dir)

    # 规范化字符串
    data_dir_text = str(data_dir_path).replace("\\", "/").strip("/")

    if data_dir_path.is_absolute():
        explicit_path = data_dir_path / filename
    else:
        explicit_path = root_dir / data_dir_path / filename

    candidates = [
        explicit_path,
    ]

    # 如果 data_dir 非空且尚未处于 testcase/data 中，再尝试映射到 testcase/data 下
    if data_dir_text and not data_dir_text.startswith("testcase/data"):
        candidates.append(new_base / data_dir_path / filename)

    candidates.extend(
        [
            new_base / filename,
            new_base / "portal" / filename,
            new_base / "admin" / filename,
            new_base / "integration" / filename,
        ]
    )

    unique_paths = []
    seen = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique_paths.append(path)
    return unique_paths


def _resolve_json_path(filename, data_dir):
    root_dir = project_root()
    for file_path in _candidate_paths(root_dir, filename, data_dir):
        if file_path.exists():
            return file_path
    raise FileNotFoundError(
        f"json 格式文件不存在: filename={filename}, data_dir={data_dir}"
    )


def load_json(filename, data_dir="testcase/data"):
    file_path = _resolve_json_path(filename, data_dir)

    if file_path.stat().st_size == 0:
        raise ValueError(f"json文件的内容为空: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"文件非json格式: {file_path}") from e


def load_json_data(filename, fields, data_dir="testcase/data"):
    if not isinstance(fields, list | tuple) or not fields:
        raise ValueError(
            f"load_json_data传入的参数必须是列表或元组，fields参数: {fields}"
        )

    raw = load_json(filename, data_dir)

    if not isinstance(raw, list):
        raise TypeError(f"{filename} json文件的根结构必须是list: {type(raw).__name__}")

    result = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise TypeError(
                f"{filename} item #{index + 1} 必须是字典: {type(item).__name__}"
            )

        missing = [field for field in fields if field not in item]
        if missing:
            raise KeyError(f"{filename} item {index + 1} 参数不存在: {missing}")

        result.append(tuple(item[field] for field in fields))

    return result
