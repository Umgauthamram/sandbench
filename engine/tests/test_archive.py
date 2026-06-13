import base64
import io
import zipfile
import tarfile
import pytest

from sandbox.archive import extract_archive

def create_zip_payload(files: dict, symlinks: dict = None, zip_bomb_ratio: bool = False) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in files.items():
            if zip_bomb_ratio:
                # To simulate a zip bomb with huge compression ratio, we write heavily compressed data.
                # A string of all "A"s compresses extremely well.
                z.writestr(name, content, compress_type=zipfile.ZIP_DEFLATED)
            else:
                z.writestr(name, content)
        if symlinks:
            for name, target in symlinks.items():
                info = zipfile.ZipInfo(name)
                info.external_attr = 0xA0000000  # Unix symlink attribute
                z.writestr(info, target)
    return buf.getvalue()

def create_tar_payload(files: dict, symlinks: dict = None, special_file: bool = False) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in files.items():
            content_bytes = content.encode("utf-8")
            ti = tarfile.TarInfo(name=name)
            ti.size = len(content_bytes)
            ti.mode = 0o644
            tar.addfile(ti, io.BytesIO(content_bytes))
        if symlinks:
            for name, target in symlinks.items():
                ti = tarfile.TarInfo(name=name)
                ti.type = tarfile.SYMTYPE
                ti.linkname = target
                tar.addfile(ti)
        if special_file:
            ti = tarfile.TarInfo(name="fifo_dev")
            ti.type = tarfile.FIFOTYPE
            tar.addfile(ti)
    return buf.getvalue()


def test_valid_zip():
    files = {
        "solution.py": "def fizzbuzz(n): pass",
        "helper.py": "def help(): pass",
        "data.json": '{"config": true}'
    }
    raw = create_zip_payload(files)
    res, reason = extract_archive(raw, "zip")
    assert reason == "ok"
    assert res is not None
    assert res == {
        "/workspace/solution.py": "def fizzbuzz(n): pass",
        "/workspace/helper.py": "def help(): pass",
        "/workspace/data.json": '{"config": true}'
    }


def test_valid_tar_gz():
    files = {
        "solution.py": "def fizzbuzz(n): pass",
        "helper.py": "def help(): pass",
        "data.json": '{"config": true}'
    }
    raw = create_tar_payload(files)
    res, reason = extract_archive(raw, "targz")
    assert reason == "ok"
    assert res is not None
    assert res == {
        "/workspace/solution.py": "def fizzbuzz(n): pass",
        "/workspace/helper.py": "def help(): pass",
        "/workspace/data.json": '{"config": true}'
    }


def test_subdirectory_paths_preserved():
    files = {
        "my-project-main/solution.py": "def fizzbuzz(n): pass",
        "my-project-main/helper.py": "def help(): pass",
        "my-project-main/subdir/data.json": '{"config": true}'
    }
    raw = create_zip_payload(files)
    res, reason = extract_archive(raw, "zip")
    assert reason == "ok"
    assert res is not None
    assert res == {
        "/workspace/my-project-main/solution.py": "def fizzbuzz(n): pass",
        "/workspace/my-project-main/helper.py": "def help(): pass",
        "/workspace/my-project-main/subdir/data.json": '{"config": true}'
    }


def test_path_traversal_rejection():
    # Relative path traversal
    files = {
        "solution.py": "...",
        "../../escape.py": "malicious"
    }
    raw = create_zip_payload(files)
    res, reason = extract_archive(raw, "zip")
    assert res is None
    assert "path traversal" in reason

    # Absolute path check
    files_abs = {
        "solution.py": "...",
        "/etc/passwd": "malicious"
    }
    raw_abs = create_tar_payload(files_abs)
    res_abs, reason_abs = extract_archive(raw_abs, "targz")
    assert res_abs is None
    assert "path traversal" in reason_abs


def test_symlink_rejection():
    # ZIP symlink
    files = {"solution.py": "..."}
    symlinks = {"link.py": "/etc/passwd"}
    raw_zip = create_zip_payload(files, symlinks)
    res_zip, reason_zip = extract_archive(raw_zip, "zip")
    assert res_zip is None
    assert "symlink" in reason_zip

    # Tar.Gz symlink
    raw_tar = create_tar_payload(files, symlinks)
    res_tar, reason_tar = extract_archive(raw_tar, "targz")
    assert res_tar is None
    assert "symlink" in reason_tar


def test_special_file_rejection():
    files = {"solution.py": "..."}
    raw_tar = create_tar_payload(files, special_file=True)
    res_tar, reason_tar = extract_archive(raw_tar, "targz")
    assert res_tar is None
    assert "special files" in reason_tar


def test_zip_bomb_ratio_rejection():
    # Large file of repeating characters that compresses extremely well
    files = {
        "solution.py": "def fizzbuzz(n): pass",
        "bomb.txt": "A" * (100 * 1024) # 100 KB uncompressed
    }
    # Compress with ZIP_DEFLATED to trigger high compression ratio
    raw = create_zip_payload(files, zip_bomb_ratio=True)
    res, reason = extract_archive(raw, "zip")
    assert res is None
    assert "ratio" in reason


def test_nesting_depth_limit():
    files = {
        "solution.py": "...",
        "1/2/3/4/5/6/7/8/9/10/11/12/13/deep.py": "..."
    }
    raw = create_zip_payload(files)
    res, reason = extract_archive(raw, "zip")
    assert res is None
    assert "depth" in reason


def test_disallowed_file_extension():
    files = {
        "solution.py": "...",
        "malicious.exe": "..."
    }
    raw = create_zip_payload(files)
    res, reason = extract_archive(raw, "zip")
    assert res is None
    assert "extension" in reason or "not allowed" in reason


def test_file_count_limit():
    # Limit is MAX_FILES (default 200)
    files = {f"file_{i}.py": "..." for i in range(201)}
    files["solution.py"] = "..."
    raw = create_zip_payload(files)
    res, reason = extract_archive(raw, "zip")
    assert res is None
    assert "count" in reason


def test_single_file_size_limit():
    # Limit is MAX_FILE_SIZE (default 1 MB)
    files = {
        "solution.py": "...",
        "large_file.py": "a" * (1024 * 1024 + 1)
    }
    raw = create_zip_payload(files)
    res, reason = extract_archive(raw, "zip")
    assert res is None
    assert "size" in reason


def test_non_utf8_rejection():
    # Write some non-UTF-8 binary data into helper.py
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("solution.py", "def fizzbuzz(): pass")
        z.writestr("helper.py", b"\x80\x81\x82\x83")
    raw = buf.getvalue()
    res, reason = extract_archive(raw, "zip")
    assert res is None
    assert "non-UTF8" in reason


def test_second_pass_total_cap():
    # Builds a zip whose per-file sizes each pass but whose TOTAL exceeds MAX_UNCOMPRESSED.
    # Max file size is 1 MB (passes 600 KB).
    # 9 files of 600 KB = 5.4 MB, which exceeds MAX_UNCOMPRESSED (default 5 MB).
    files = {
        "solution.py": "def fizzbuzz(n): pass",
    }
    for i in range(9):
        files[f"helper_{i}.py"] = "A" * (600 * 1024)
        
    raw = create_zip_payload(files)
    res, reason = extract_archive(raw, "zip")
    assert res is None
    assert "total uncompressed" in reason
