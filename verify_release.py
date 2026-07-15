from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import struct
import sys
import zlib
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "release-manifest.json"
CHECKSUM_PATH = ROOT / "SHA256SUMS.txt"
RELEASE_NAME = "Spreadsheet-Data-Quality-Audit-Sample-v1.0.0.zip"
RELEASE_PATH = ROOT / "release" / RELEASE_NAME
ZIP_PREFIX = "Spreadsheet-Data-Quality-Audit-Sample-v1.0.0/"
FIXED_TIMESTAMP = (2026, 7, 15, 0, 0, 0)

EXPECTED_REPOSITORY_URL = "https://github.com/ja9740913/spreadsheet-data-quality-audit-sample"
EXPECTED_RELEASE_URL = f"{EXPECTED_REPOSITORY_URL}/releases/tag/v1.0.0"
EXPECTED_RELEASE_ASSET_URL = f"{EXPECTED_REPOSITORY_URL}/releases/download/v1.0.0/{RELEASE_NAME}"
GITHUB_RELEASE_API_URL = (
    "https://api.github.com/repos/ja9740913/"
    "spreadsheet-data-quality-audit-sample/releases/tags/v1.0.0"
)

EXPECTED_CONTENT_URLS = {
    "https://payment-flow-studio-tw.masstech.chatgpt.site/en/tools/"
    "spreadsheet-data-quality-audit-toolkit?source=github_e21_sample",
    "https://payment-flow-studio-tw.masstech.chatgpt.site/en/tools/"
    "spreadsheet-data-quality-audit-toolkit?source=github_e21_sample_release",
    "https://toolcraftstudio.gumroad.com/l/spreadsheet-data-quality-audit-toolkit",
    "https://payment-flow-studio-tw.masstech.chatgpt.site/en/terms/"
    "spreadsheet-data-quality-audit-toolkit-v1",
}
PREPARED_HOST_URLS = {
    "https://payment-flow-studio-tw.masstech.chatgpt.site/",
    "https://toolcraftstudio.gumroad.com/",
}

PREPARED_STATUS_MARKER = (
    "> Publication status: prepared locally for a future public GitHub repository. "
    "No remote repository or GitHub release has been created, and the preparation process "
    "performed no external write."
)
PUBLISHED_STATUS_MARKER = (
    f"> Publication status: published at {EXPECTED_REPOSITORY_URL}. "
    f"The verified v1.0.0 release is available at {EXPECTED_RELEASE_URL}."
)

EXPECTED_FILES = {
    "README.md",
    "FREE-SAMPLE-LICENSE.txt",
    "RELEASE-README.txt",
    "SECURITY.md",
    "release-manifest.json",
    "SHA256SUMS.txt",
    "verify_release.py",
    f"release/{RELEASE_NAME}",
    "assets/cover-1200x1200.png",
    "assets/report-preview-1200x1200.png",
    "sample/fictional-orders-with-issues.xlsx",
    "sample-output/audit-report.xlsx",
    "sample-output/audit-summary.md",
    "sample-output/audit-manifest.json",
}

ZIP_SOURCE_PATHS = [
    ("RELEASE-README.txt", ROOT / "RELEASE-README.txt"),
    ("FREE-SAMPLE-LICENSE.txt", ROOT / "FREE-SAMPLE-LICENSE.txt"),
    ("sample/fictional-orders-with-issues.xlsx", ROOT / "sample" / "fictional-orders-with-issues.xlsx"),
    ("sample-output/audit-report.xlsx", ROOT / "sample-output" / "audit-report.xlsx"),
    ("sample-output/audit-summary.md", ROOT / "sample-output" / "audit-summary.md"),
    ("sample-output/audit-manifest.json", ROOT / "sample-output" / "audit-manifest.json"),
]
EXPECTED_ZIP_MEMBERS = [ZIP_PREFIX + name for name, _ in ZIP_SOURCE_PATHS] + [ZIP_PREFIX + "SHA256SUMS.txt"]

EXPECTED_HASHED_PATHS = [
    f"release/{RELEASE_NAME}",
    "assets/cover-1200x1200.png",
    "assets/report-preview-1200x1200.png",
    "sample/fictional-orders-with-issues.xlsx",
    "sample-output/audit-report.xlsx",
    "sample-output/audit-summary.md",
    "sample-output/audit-manifest.json",
]

PUBLIC_TEXT_FILES = {
    "README.md",
    "FREE-SAMPLE-LICENSE.txt",
    "RELEASE-README.txt",
    "SECURITY.md",
    "release-manifest.json",
    "SHA256SUMS.txt",
}

URL_RE = re.compile(r"https://[^\s<>)\]\\\"']+")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
ABSOLUTE_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/](?:Users|Documents|OneDrive)[\\/]|/home/|/Users/)")
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret|otp)\b\s*[:=]\s*[\"']?[^\s,}\"']{6,}"
)
FORBIDDEN_PUBLIC_NAMES = {
    "audit_toolkit.py",
    "run-audit.ps1",
    "spreadsheet-data-quality-audit-toolkit-v1.0.0.zip",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(expected_state: str) -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    require(manifest["schema_version"] == 1, "unsupported manifest schema")
    require(
        manifest["sample"]["name"] == "Spreadsheet Data Quality Audit Fictional Sample",
        "sample identity mismatch",
    )
    require(manifest["sample"]["version"] == "1.0.0", "release version mismatch")
    require(manifest["repository"] == {
        "owner": "ja9740913",
        "name": "spreadsheet-data-quality-audit-sample",
        "visibility": "public",
        "description": (
            "Complete fictional XLSX input with redacted Excel, Markdown, and JSON data-quality audit outputs. "
            "Sample only—no audit engine, launcher, customer data, or commercial license."
        ),
        "topics": ["data-quality", "spreadsheet", "excel", "xlsx", "data-validation", "sample-data"],
    }, "repository settings changed")
    expected_status = "prepared-local-only" if expected_state == "prepared" else "published"
    require(manifest["sample"]["publication_status"] == expected_status, f"publication status is not {expected_status}")
    return manifest


def verify_inventory(expected_state: str) -> None:
    found = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(ROOT).parts
    }
    require(
        found == EXPECTED_FILES,
        f"unexpected public inventory: missing={sorted(EXPECTED_FILES - found)} extra={sorted(found - EXPECTED_FILES)}",
    )
    if expected_state == "prepared":
        require(not (ROOT / ".git").exists(), "nested Git metadata exists in prepared state")
    for relative in found:
        path = ROOT / relative
        require(not path.is_symlink(), f"symlinks are not allowed: {relative}")
        require(path.name.casefold() not in FORBIDDEN_PUBLIC_NAMES, f"forbidden paid payload detected: {relative}")
    require(
        [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.zip")] == [f"release/{RELEASE_NAME}"],
        "the package must contain exactly one sample ZIP",
    )
    python_files = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.py"))
    require(python_files == ["verify_release.py"], f"unexpected Python payload: {python_files}")
    require(not any(ROOT.rglob("*.ps1")), "PowerShell launcher or script is not allowed in the sample package")


def parse_checksums() -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line_number, line in enumerate(CHECKSUM_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        require(match is not None, f"invalid checksum line {line_number}")
        digest, relative = match.groups()
        require(relative not in checksums, f"duplicate checksum path: {relative}")
        checksums[relative] = digest
    require(list(checksums) == EXPECTED_HASHED_PATHS, "outer checksum inventory or order changed")
    return checksums


def verify_hashes(manifest: dict) -> dict[str, str]:
    checksums = parse_checksums()
    assets = {item["path"]: item for item in manifest["assets"]}
    require(list(assets) == EXPECTED_HASHED_PATHS, "manifest asset inventory or order changed")
    require(set(assets) == set(checksums), "manifest assets and SHA256SUMS.txt differ")
    for relative, expected in checksums.items():
        path = ROOT / relative
        item = assets[relative]
        require(item["public"] is True, f"asset not marked public: {relative}")
        require(item["sha256"] == expected, f"manifest SHA mismatch: {relative}")
        require(item["bytes"] == path.stat().st_size, f"manifest byte count mismatch: {relative}")
        require(sha256(path) == expected, f"SHA-256 mismatch: {relative}")
    return checksums


def verify_text_safety() -> None:
    for relative in PUBLIC_TEXT_FILES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        require("-----BEGIN PRIVATE KEY-----" not in text, f"private key material in {relative}")
        require(not EMAIL_RE.search(text), f"email address detected in {relative}")
        require(not ABSOLUTE_PATH_RE.search(text), f"local absolute path detected in {relative}")
        require(not SECRET_ASSIGNMENT_RE.search(text), f"credential-like assignment detected in {relative}")


def verify_local_links() -> None:
    for relative in PUBLIC_TEXT_FILES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for target in MARKDOWN_LINK_RE.findall(text):
            target = target.strip().strip("<>")
            if target.startswith(("https://", "#")):
                continue
            local_part = target.split("#", 1)[0]
            require(local_part != "", f"empty local link in {relative}")
            require((ROOT / local_part).is_file(), f"broken local link in {relative}: {target}")


def extract_urls() -> set[str]:
    urls: set[str] = set()
    for relative in PUBLIC_TEXT_FILES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        urls.update(match.rstrip(".,;:!?") for match in URL_RE.findall(text))
    return urls


def check_live_url(url: str) -> tuple[int, str]:
    headers = {"User-Agent": "E21-Fictional-Sample-Verifier/1.0"}
    for method in ("HEAD", "GET"):
        request = Request(url, headers=headers, method=method)
        try:
            with urlopen(request, timeout=20) as response:
                status = response.getcode()
                require(200 <= status < 400, f"link returned HTTP {status}: {url}")
                return status, response.geturl()
        except HTTPError as exc:
            if method == "HEAD" and exc.code in {403, 405}:
                continue
            raise AssertionError(f"link returned HTTP {exc.code}: {url}") from exc
        except URLError as exc:
            raise AssertionError(f"link check failed: {url}: {exc.reason}") from exc
    raise AssertionError(f"link check failed: {url}")


def verify_urls(manifest: dict, offline: bool, expected_state: str) -> list[tuple[str, int, str]]:
    require(set(manifest["links"].values()) == EXPECTED_CONTENT_URLS, "manifest content URL set changed")
    found_urls = extract_urls()
    expected_urls = set(EXPECTED_CONTENT_URLS)
    if expected_state == "published":
        expected_urls.update({EXPECTED_REPOSITORY_URL, EXPECTED_RELEASE_URL, EXPECTED_RELEASE_ASSET_URL})
    require(
        found_urls == expected_urls,
        f"unapproved or missing URL: expected={sorted(expected_urls)} found={sorted(found_urls)}",
    )
    verify_local_links()
    if offline:
        return []
    live_targets = PREPARED_HOST_URLS if expected_state == "prepared" else found_urls - {EXPECTED_RELEASE_ASSET_URL}
    return [(url, *check_live_url(url)) for url in sorted(live_targets)]


def validate_external_state_contract(manifest: dict, expected_state: str) -> None:
    state = manifest["external_state"]
    require(
        set(state)
        == {
            "remote_repository_created",
            "remote_repository_url",
            "github_release_created",
            "github_release_url",
            "release_asset_url",
            "files_uploaded",
            "published_at",
            "external_write_performed_by_preparation",
        },
        "external-state schema changed",
    )
    require(state["external_write_performed_by_preparation"] is False, "preparation may not claim an external write")
    if expected_state == "prepared":
        require(state["remote_repository_created"] is False, "manifest claims a remote repository exists")
        require(state["remote_repository_url"] is None, "manifest contains a prepared-state repository URL")
        require(state["github_release_created"] is False, "manifest claims a GitHub release exists")
        require(state["github_release_url"] is None, "manifest contains a prepared-state release URL")
        require(state["release_asset_url"] is None, "manifest contains a prepared-state release asset URL")
        require(state["files_uploaded"] is False, "manifest claims files were uploaded")
        require(state["published_at"] is None, "manifest contains a prepared-state publication timestamp")
    else:
        require(state["remote_repository_created"] is True, "manifest does not confirm the public repository")
        require(state["remote_repository_url"] == EXPECTED_REPOSITORY_URL, "published repository URL mismatch")
        require(state["github_release_created"] is True, "manifest does not confirm the GitHub release")
        require(state["github_release_url"] == EXPECTED_RELEASE_URL, "published release URL mismatch")
        require(state["release_asset_url"] == EXPECTED_RELEASE_ASSET_URL, "published release asset URL mismatch")
        require(state["files_uploaded"] is True, "manifest does not confirm uploaded files")
        require(
            isinstance(state["published_at"], str)
            and re.fullmatch(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})", state["published_at"]),
            "published_at is not RFC 3339 at seconds precision",
        )


def verify_contract_fixtures(manifest: dict) -> None:
    prepared = json.loads(json.dumps(manifest))
    prepared["sample"]["publication_status"] = "prepared-local-only"
    prepared["external_state"] = {
        "remote_repository_created": False,
        "remote_repository_url": None,
        "github_release_created": False,
        "github_release_url": None,
        "release_asset_url": None,
        "files_uploaded": False,
        "published_at": None,
        "external_write_performed_by_preparation": False,
    }
    validate_external_state_contract(prepared, "prepared")
    published = json.loads(json.dumps(prepared))
    published["sample"]["publication_status"] = "published"
    published["external_state"].update(
        {
            "remote_repository_created": True,
            "remote_repository_url": EXPECTED_REPOSITORY_URL,
            "github_release_created": True,
            "github_release_url": EXPECTED_RELEASE_URL,
            "release_asset_url": EXPECTED_RELEASE_ASSET_URL,
            "files_uploaded": True,
            "published_at": "2026-07-15T09:00:00+08:00",
        }
    )
    validate_external_state_contract(published, "published")
    published["external_state"]["remote_repository_url"] = "https://github.com/example/wrong"
    try:
        validate_external_state_contract(published, "published")
    except AssertionError:
        pass
    else:
        raise AssertionError("published-state contract accepted a wrong repository URL")


def verify_count_semantics(manifest: dict) -> None:
    scope = manifest["sample_scope"]
    require(scope["finding_records"] == 16, "manifest finding-record count changed")
    require(scope["distinct_issue_codes"] == 10, "manifest distinct issue-code count changed")
    require(scope["issue_categories"] == 16, "legacy issue_categories value changed")
    require(
        scope["issue_categories_field_status"]
        == "legacy-compatible finding-record count, not distinct-code count",
        "legacy count semantics changed",
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    release_readme = (ROOT / "RELEASE-README.txt").read_text(encoding="utf-8")
    require("16 finding records across 10 distinct issue codes" in readme, "README count semantics missing")
    require("16 finding records across 10 distinct issue codes" in release_readme, "release count semantics missing")
    require("legacy field label `issue_categories`" in readme, "README legacy-field disclosure missing")
    require("legacy label issue_categories" in release_readme, "release legacy-field disclosure missing")


def verify_readme_publication_marker(expected_state: str) -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    expected = PREPARED_STATUS_MARKER if expected_state == "prepared" else PUBLISHED_STATUS_MARKER
    forbidden = PUBLISHED_STATUS_MARKER if expected_state == "prepared" else PREPARED_STATUS_MARKER
    require(expected in text, f"README publication marker does not match {expected_state} state")
    require(forbidden not in text, "README contains conflicting publication states")
    require("python -B .\\verify_release.py --state published" in text, "published verification command missing")
    require("python -B .\\verify_release.py --state prepared" in text, "prepared verification command missing")


def verify_workbook(path: Path, require_fictional_creator: bool) -> None:
    with ZipFile(path) as workbook:
        require(workbook.testzip() is None, f"corrupt workbook container: {path.name}")
        names = workbook.namelist()
        lower_names = [name.lower() for name in names]
        require("xl/vbaproject.bin" not in lower_names, f"VBA project detected: {path.name}")
        require(not any("/externallinks/" in name for name in lower_names), f"external workbook link detected: {path.name}")
        require("xl/connections.xml" not in lower_names, f"external connection detected: {path.name}")
        core = workbook.read("docProps/core.xml").decode("utf-8")
        if require_fictional_creator:
            require("fictional" in core.casefold(), f"fictional creator metadata missing: {path.name}")
        xml_text = "\n".join(
            workbook.read(name).decode("utf-8")
            for name in names
            if name.endswith((".xml", ".rels"))
        )
        require(not EMAIL_RE.search(xml_text), f"email address detected in workbook: {path.name}")
        require(not ABSOLUTE_PATH_RE.search(xml_text), f"local path detected in workbook: {path.name}")
        require("-----BEGIN PRIVATE KEY-----" not in xml_text, f"private key detected in workbook: {path.name}")


def read_png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"invalid PNG signature: {path.name}")
    require(len(data) >= 24 and data[12:16] == b"IHDR", f"missing PNG IHDR: {path.name}")
    offset = 8
    chunks: list[bytes] = []
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        payload_end = offset + 8 + length
        require(payload_end + 4 <= len(data), f"truncated PNG chunk: {path.name}")
        payload = data[offset + 8 : payload_end]
        recorded_crc = struct.unpack(">I", data[payload_end : payload_end + 4])[0]
        require(zlib.crc32(chunk_type + payload) & 0xFFFFFFFF == recorded_crc, f"PNG CRC mismatch: {path.name}")
        chunks.append(chunk_type)
        offset = payload_end + 4
        if chunk_type == b"IEND":
            break
    require(offset == len(data), f"unexpected bytes after PNG IEND: {path.name}")
    require(chunks[0] == b"IHDR" and chunks[-1] == b"IEND", f"invalid PNG chunk order: {path.name}")
    require(set(chunks) <= {b"IHDR", b"pHYs", b"IDAT", b"IEND"}, f"unapproved PNG metadata: {path.name}")
    return struct.unpack(">II", data[16:24])


def verify_pngs(manifest: dict) -> None:
    assets = {item["path"]: item for item in manifest["assets"]}
    for relative in ("assets/cover-1200x1200.png", "assets/report-preview-1200x1200.png"):
        size = read_png_size(ROOT / relative)
        require(size == (1200, 1200), f"PNG is not 1200x1200: {relative}")
        require(size == (assets[relative]["width"], assets[relative]["height"]), f"manifest PNG dimensions changed: {relative}")


def zip_info(name: str) -> ZipInfo:
    info = ZipInfo(ZIP_PREFIX + name, FIXED_TIMESTAMP)
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = ZIP_DEFLATED
    info.extra = b""
    info.comment = b""
    return info


def expected_release_bytes() -> bytes:
    internal_checksums = "".join(
        f"{sha256(path)}  {name}\n" for name, path in ZIP_SOURCE_PATHS
    ).encode("utf-8")
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in ZIP_SOURCE_PATHS:
            archive.writestr(zip_info(name), path.read_bytes(), compresslevel=9)
        archive.writestr(zip_info("SHA256SUMS.txt"), internal_checksums, compresslevel=9)
    return buffer.getvalue()


def verify_release_zip(checksums: dict[str, str]) -> None:
    actual = RELEASE_PATH.read_bytes()
    require(actual == expected_release_bytes(), "release ZIP is not the deterministic build of the approved sample inputs")
    with ZipFile(io.BytesIO(actual)) as archive:
        require(archive.testzip() is None, "release ZIP failed CRC validation")
        require(archive.namelist() == EXPECTED_ZIP_MEMBERS, f"release ZIP inventory changed: {archive.namelist()}")
        require(all(not item.flag_bits & 0x1 for item in archive.infolist()), "encrypted ZIP member detected")
        require(not any(name.casefold().endswith((".py", ".ps1")) for name in archive.namelist()), "executable source or launcher detected in release")
        internal: dict[str, str] = {}
        checksum_member = ZIP_PREFIX + "SHA256SUMS.txt"
        for line in archive.read(checksum_member).decode("utf-8").splitlines():
            match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
            require(match is not None, "invalid internal checksum line")
            digest, name = match.groups()
            require(name not in internal, f"duplicate internal checksum: {name}")
            internal[name] = digest
        require(list(internal) == [name for name, _ in ZIP_SOURCE_PATHS], "internal checksum inventory changed")
        for name, expected in internal.items():
            require(
                sha256_bytes(archive.read(ZIP_PREFIX + name)) == expected,
                f"internal release hash mismatch: {name}",
            )
        for name, path in ZIP_SOURCE_PATHS:
            public_relative = path.relative_to(ROOT).as_posix()
            expected = checksums.get(public_relative, sha256(path))
            require(
                sha256_bytes(archive.read(ZIP_PREFIX + name)) == expected,
                f"release member and public copy differ: {name}",
            )


def verify_sample_evidence() -> None:
    source = ROOT / "sample" / "fictional-orders-with-issues.xlsx"
    report = ROOT / "sample-output" / "audit-report.xlsx"
    summary = ROOT / "sample-output" / "audit-summary.md"
    evidence = json.loads((ROOT / "sample-output" / "audit-manifest.json").read_text(encoding="utf-8"))
    require(evidence["state"] == "AUDIT_GENERATED_NOT_CLIENT_DELIVERED", "sample evidence state changed")
    require(evidence["source"]["file_name"] == source.name, "sample source filename mismatch")
    require(evidence["source"]["sha256"] == sha256(source), "sample source SHA mismatch")
    require(evidence["source"]["data_row_values_copied_to_outputs"] is False, "sample claims data-row values were copied")
    require(evidence["scope"]["rows_scanned"] == 26, "sample row count changed")
    require(evidence["scope"]["columns_scanned"] == 6, "sample column count changed")
    require(evidence["summary"]["issue_categories"] == 16, "sample legacy finding-record count changed")
    require(evidence["summary"]["data_row_values_in_output"] == 0, "sample output contains data-row values")
    require(evidence["external_actions"] == 0, "sample manifest claims an external action")
    output_hashes = {item["file"]: item["sha256"] for item in evidence["outputs"]}
    require(output_hashes == {"audit-report.xlsx": sha256(report), "audit-summary.md": sha256(summary)}, "sample output hashes changed")
    summary_text = summary.read_text(encoding="utf-8")
    require("Scanned: 26 data rows × 6 columns" in summary_text, "sample summary scope changed")
    require("Issue categories: 16" in summary_text, "sample legacy summary count changed")
    require("Original data-row cell values copied into this report: no" in summary_text, "sample redaction statement missing")
    finding_lines = [
        line
        for line in summary_text.splitlines()
        if re.match(r"^\| (?:HIGH|MEDIUM|REVIEW) \| [A-Z_]+ \|", line)
    ]
    require(len(finding_lines) == 16, "sample does not contain 16 finding records")
    issue_codes = {line.split("|")[2].strip() for line in finding_lines}
    require(len(issue_codes) == 10, "sample does not contain 10 distinct issue codes")


def verify_remote_publication() -> tuple[int, int, int]:
    repo_status, _ = check_live_url(EXPECTED_REPOSITORY_URL)
    release_status, _ = check_live_url(EXPECTED_RELEASE_URL)
    request = Request(
        GITHUB_RELEASE_API_URL,
        headers={"User-Agent": "E21-Fictional-Sample-Verifier/1.0", "Accept": "application/vnd.github+json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (HTTPError, URLError) as exc:
        raise AssertionError(f"GitHub release API check failed: {exc}") from exc
    require(payload["tag_name"] == "v1.0.0", "GitHub release tag mismatch")
    require(payload["draft"] is False and payload["prerelease"] is False, "GitHub release is not final/public")
    assets = payload["assets"]
    require(len(assets) == 1, "GitHub release must have exactly one asset")
    asset = assets[0]
    require(asset["name"] == RELEASE_NAME, "GitHub release asset name mismatch")
    require(asset["browser_download_url"] == EXPECTED_RELEASE_ASSET_URL, "GitHub release asset URL mismatch")
    require(asset["size"] == RELEASE_PATH.stat().st_size, "GitHub release asset size mismatch")
    download_request = Request(EXPECTED_RELEASE_ASSET_URL, headers={"User-Agent": "E21-Fictional-Sample-Verifier/1.0"})
    try:
        with urlopen(download_request, timeout=30) as response:
            remote_bytes = response.read()
    except (HTTPError, URLError) as exc:
        raise AssertionError(f"GitHub release asset download failed: {exc}") from exc
    require(sha256_bytes(remote_bytes) == sha256(RELEASE_PATH), "GitHub release asset SHA-256 mismatch")
    return repo_status, release_status, len(remote_bytes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the E21 fictional public sample package.")
    parser.add_argument("--offline", action="store_true", help="skip live HTTP checks")
    parser.add_argument("--state", choices=("prepared", "published"), default="prepared")
    args = parser.parse_args()

    manifest = load_manifest(args.state)
    verify_contract_fixtures(manifest)
    verify_count_semantics(manifest)
    verify_inventory(args.state)
    checksums = verify_hashes(manifest)
    verify_text_safety()
    validate_external_state_contract(manifest, args.state)
    verify_readme_publication_marker(args.state)
    verify_workbook(ROOT / "sample" / "fictional-orders-with-issues.xlsx", require_fictional_creator=True)
    verify_workbook(ROOT / "sample-output" / "audit-report.xlsx", require_fictional_creator=False)
    verify_pngs(manifest)
    verify_sample_evidence()
    verify_release_zip(checksums)
    live_results = verify_urls(manifest, args.offline, args.state)
    remote_result = None
    if args.state == "published" and not args.offline:
        remote_result = verify_remote_publication()

    print("E21 fictional public sample verifier passed")
    print(f"Inventory: {len(EXPECTED_FILES)} exact files / one deterministic sample-only ZIP")
    print("Sample: 26 fictional rows / 6 columns / 16 finding records across 10 issue codes / redacted outputs")
    print("Leak gate: no paid engine, PowerShell launcher, buyer ZIP, executable source, credential, email, or local path")
    if args.state == "prepared":
        print("External state: prepared locally / no nested repository / no GitHub release / no upload")
    else:
        print("External state: manifest, README, repository, release, and single release asset agree")
    if args.offline:
        print("Links: approved URL contract recorded; live HTTP checks skipped by --offline")
    else:
        for url, status, final_url in live_results:
            print(f"Link: HTTP {status} {url} -> {final_url}")
        if args.state == "prepared":
            print("Prospective exact product links remain contract-only until publication; host roots are live")
        if remote_result is not None:
            print(
                f"GitHub publication: repository HTTP {remote_result[0]} / release HTTP {remote_result[1]} / "
                f"one SHA-matched asset ({remote_result[2]} bytes)"
            )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"VERIFY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
