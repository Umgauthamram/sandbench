"""Safe archive extraction and validation for SandBench.
"""
import io
import os
import re
import zipfile
import tarfile
import logging
from typing import Dict, Tuple, Optional

# Import the limits from config
from config import (
    MAX_UNCOMPRESSED,
    MAX_FILES,
    MAX_FILE_SIZE,
    MAX_DEPTH,
    RATIO_LIMIT
)

logger = logging.getLogger(__name__)

def is_ignored(path: str) -> bool:
    """Ignore macOS metadata, pycache, and git internal files."""
    parts = path.replace("\\", "/").split("/")
    for p in parts:
        if p in ("__pycache__", ".git", ".DS_Store") or p.startswith("._"):
            return True
    return False

def is_invalid_path(path: str) -> bool:
    """Check if path is absolute, has a drive letter, or contains traversal components."""
    normalized = path.replace("\\", "/")
    if normalized.startswith("/"):
        return True
    if re.match(r"^[a-zA-Z]:", normalized):
        return True
    parts = normalized.split("/")
    if ".." in parts:
        return True
    return False

def extract_archive(raw_bytes: bytes, kind: str) -> Tuple[Optional[Dict[str, str]], str]:
    """Validate and extract files from a ZIP or Tar.Gz archive.

    Args:
        raw_bytes: Binary contents of the archive.
        kind: 'zip' or 'targz'.

    Returns:
        (file_map, 'ok') on success, or (None, reason) on failure/rejection.
    """
    try:
        if not raw_bytes:
            return None, "empty archive"

        if kind not in ("zip", "targz"):
            return None, "invalid archive kind"

        raw_file_map: Dict[str, str] = {}
        total_size = 0
        file_count = 0
        allowed_exts = {".py", ".js", ".json", ".txt", ".md", ".yaml", ".yml", ".ini", ".cfg", ".toml"}

        if kind == "zip":
            try:
                z_file = io.BytesIO(raw_bytes)
                with zipfile.ZipFile(z_file) as z:
                    infolist = z.infolist()
                    
                    # --- FIRST PASS: Validate metadata ---
                    for info in infolist:
                        is_dir = info.is_dir() or info.filename.endswith("/")
                        name = info.filename
                        if is_ignored(name):
                            continue

                        # Path checks
                        if is_invalid_path(name):
                            return None, "path traversal or absolute path detected"

                        # Depth check
                        normalized = name.replace("\\", "/").strip("/")
                        path_parts = [p for p in normalized.split("/") if p]
                        if len(path_parts) > MAX_DEPTH:
                            return None, "directory depth limit exceeded"

                        # Symlink check (detect symlink mode bits: external_attr MSB 0xA000 indicates symlink)
                        if (info.external_attr >> 16) & 0xF000 == 0xA000:
                            return None, "symlinks and hardlinks are not allowed"

                        if is_dir:
                            continue

                        # Extension check
                        _, ext = os.path.splitext(normalized.lower())
                        if ext not in allowed_exts:
                            return None, f"disallowed file extension: {ext}"

                        # Size check per file
                        if info.file_size > MAX_FILE_SIZE:
                            return None, "file size limit exceeded"

                        # Ratio check (zip bomb detection)
                        if info.compress_size == 0:
                            ratio = 1000.0 if info.file_size > 0 else 1.0
                        else:
                            ratio = info.file_size / info.compress_size
                        if ratio > RATIO_LIMIT:
                            return None, "compression ratio limit exceeded"

                        # Accumulate
                        total_size += info.file_size
                        if total_size > MAX_UNCOMPRESSED:
                            return None, "total uncompressed size limit exceeded"

                        file_count += 1
                        if file_count > MAX_FILES:
                            return None, "file count limit exceeded"

                    # --- SECOND PASS: Decompress and read content ---
                    total_read = 0
                    for info in infolist:
                        is_dir = info.is_dir() or info.filename.endswith("/")
                        if is_dir or is_ignored(info.filename):
                            continue

                        with z.open(info) as f:
                            content_bytes = f.read(MAX_FILE_SIZE + 1)
                            if len(content_bytes) > MAX_FILE_SIZE:
                                return None, "file size limit exceeded"
                            
                            total_read += len(content_bytes)
                            if total_read > MAX_UNCOMPRESSED:
                                return None, "total uncompressed size limit exceeded"
                            
                            try:
                                content_str = content_bytes.decode("utf-8")
                            except UnicodeDecodeError:
                                return None, "invalid non-UTF8 file detected"
                            
                            normalized_name = info.filename.replace("\\", "/")
                            raw_file_map[normalized_name] = content_str

            except zipfile.BadZipFile as e:
                return None, f"corrupt or invalid zip: {str(e)}"

        elif kind == "targz":
            try:
                tar_file = io.BytesIO(raw_bytes)
                with tarfile.open(fileobj=tar_file, mode="r:gz") as tar:
                    # --- FIRST PASS: Validate metadata ---
                    for member in tar.getmembers():
                        name = member.name
                        if is_ignored(name):
                            continue

                        # Path checks
                        if is_invalid_path(name):
                            return None, "path traversal or absolute path detected"

                        # Depth check
                        normalized = name.replace("\\", "/").strip("/")
                        path_parts = [p for p in normalized.split("/") if p]
                        if len(path_parts) > MAX_DEPTH:
                            return None, "directory depth limit exceeded"

                        # Symlink / Hardlink check
                        if member.issym() or member.islnk():
                            return None, "symlinks and hardlinks are not allowed"
                        
                        # Special file check (only allow regular files and directories)
                        if not (member.isreg() or member.isdir()):
                            return None, "special files are not allowed"

                        if member.isdir():
                            continue

                        # Extension check
                        _, ext = os.path.splitext(normalized.lower())
                        if ext not in allowed_exts:
                            return None, f"disallowed file extension: {ext}"

                        # Size check per file
                        if member.size > MAX_FILE_SIZE:
                            return None, "file size limit exceeded"

                        # Accumulate
                        total_size += member.size
                        if total_size > MAX_UNCOMPRESSED:
                            return None, "total uncompressed size limit exceeded"

                        file_count += 1
                        if file_count > MAX_FILES:
                            return None, "file count limit exceeded"

                    # --- SECOND PASS: Decompress and read content ---
                    total_read = 0
                    for member in tar.getmembers():
                        if not member.isreg() or is_ignored(member.name):
                            continue

                        f = tar.extractfile(member)
                        if f is None:
                            return None, "failed to read archive entry"

                        content_bytes = f.read(MAX_FILE_SIZE + 1)
                        if len(content_bytes) > MAX_FILE_SIZE:
                            return None, "file size limit exceeded"

                        total_read += len(content_bytes)
                        if total_read > MAX_UNCOMPRESSED:
                            return None, "total uncompressed size limit exceeded"

                        try:
                            content_str = content_bytes.decode("utf-8")
                        except UnicodeDecodeError:
                            return None, "invalid non-UTF8 file detected"

                        normalized_name = member.name.replace("\\", "/")
                        raw_file_map[normalized_name] = content_str

            except Exception as e:
                return None, f"corrupt or invalid tar.gz: {str(e)}"

        # Strip any common root directory from paths (e.g. folder zipping wrappers)
        common_root = ""
        paths = list(raw_file_map.keys())
        if paths:
            split_paths = [p.split("/") for p in paths]
            max_check_len = min(len(p) - 1 for p in split_paths)
            if max_check_len > 0:
                common_parts = []
                for i in range(max_check_len):
                    first = split_paths[0][i]
                    if all(p[i] == first for p in split_paths):
                        common_parts.append(first)
                    else:
                        break
                if common_parts:
                    common_root = "/".join(common_parts) + "/"

        file_map = {}
        for name, content in raw_file_map.items():
            stripped_name = name
            if common_root and name.startswith(common_root):
                stripped_name = name[len(common_root):]
            file_map[f"/workspace/{stripped_name}"] = content

        return file_map, "ok"

    except Exception as e:
        logger.exception("Unexpected error during archive extraction")
        return None, f"unexpected error: {str(e)}"
