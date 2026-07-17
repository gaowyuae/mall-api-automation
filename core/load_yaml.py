from pathlib import Path

import yaml

from core.paths import project_root

DEFAULT_DATA_DIR = "data"
DEFAULT_DATA_SUBDIRS = ("portal", "admin", "integration")
YAML_EXTENSIONS = (".yaml", ".yml")


def _filename_variants(filename):
    file_path = Path(str(filename).strip())

    if file_path.suffix.lower() in YAML_EXTENSIONS:
        return [file_path]

    return [Path(f"{file_path}{suffix}") for suffix in YAML_EXTENSIONS]


def _unique_paths(paths):
    unique_paths = []
    seen = set()

    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique_paths.append(path)

    return unique_paths


def _candidate_paths(root_dir, filename, data_dir):
    data_base = root_dir / DEFAULT_DATA_DIR
    data_dir_path = Path(data_dir or DEFAULT_DATA_DIR)
    data_dir_text = str(data_dir_path).replace("\\", "/").strip("/")

    candidates = []
    for file_path in _filename_variants(filename):
        if file_path.is_absolute():
            candidates.append(file_path)
            continue

        if data_dir_path.is_absolute():
            candidates.append(data_dir_path / file_path)
            continue

        candidates.append(root_dir / data_dir_path / file_path)

        if data_dir_text and not data_dir_text.startswith(DEFAULT_DATA_DIR):
            candidates.append(data_base / data_dir_path / file_path)

        candidates.append(data_base / file_path)
        candidates.extend(
            data_base / sub_dir / file_path for sub_dir in DEFAULT_DATA_SUBDIRS
        )

    return _unique_paths(candidates)


def _resolve_yaml_path(filename, data_dir = DEFAULT_DATA_DIR):
    if not str(filename).strip():
        raise ValueError("yaml filename cannot be empty")

    root_dir = project_root()
    for file_path in _candidate_paths(root_dir, filename, data_dir):
        if file_path.is_file():
            return file_path

    raise FileNotFoundError(
        f"yaml data file not found: filename={filename}, data_dir={data_dir}"
    )


def load_yaml(filename, data_dir = DEFAULT_DATA_DIR):
    file_path = _resolve_yaml_path(filename, data_dir)

    if file_path.stat().st_size == 0:
        raise ValueError(f"yaml data file is empty: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"file is not valid yaml: {file_path}") from exc


def load_yaml_data(
    filename,
    fields,
    data_dir = DEFAULT_DATA_DIR,
):
    if not isinstance(fields, list | tuple) or not fields:
        raise ValueError(
            f"load_yaml_data fields must be a non-empty list or tuple: {fields}"
        )

    raw = load_yaml(filename, data_dir)

    if not isinstance(raw, list):
        raise TypeError(f"{filename} yaml root data must be list: {type(raw).__name__}")

    result = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise TypeError(
                f"{filename} item #{index + 1} must be dict: {type(item).__name__}"
            )

        missing = [field for field in fields if field not in item]
        if missing:
            raise KeyError(f"{filename} item #{index + 1} missing fields: {missing}")

        result.append(tuple(item[field] for field in fields))

    return result
