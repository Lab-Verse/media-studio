"""Find licensed archival images and stock footage for the scene waterfall."""

import hashlib
import json
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

import requests

from . import normalizer

LOGGER = logging.getLogger(__name__)
MAX_BYTES = 150 * 1024 * 1024
ALLOWED_HOSTS = (
    "wikimedia.org", "pexels.com", "pixabay.com", "loc.gov",
    "si.edu", "rijksmuseum.nl", "europeana.eu", "flickr.com", "staticflickr.com",
    "metmuseum.org", "artic.edu", "amsterdam.nl", "getarchive.net",
    "digitalcommonwealth.org", "nypl.org", "nasa.gov", "archives.gov",
)
IMAGE_MIME_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
VIDEO_MIME_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm"}
STOCK_PROVIDERS = ("wikimedia_commons", "openverse", "pexels_stock", "pixabay")
TIMEOUT = (5, 20)


@dataclass(frozen=True)
class Candidate:
    provider: str
    asset_id: str
    download: str
    source_url: str
    license: str
    license_url: str = ""
    creator: str = ""
    title: str = ""
    kind: str = "image"


def _allowed_download(url: str) -> bool:
    try:
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.username or parts.password or parts.port not in {None, 443}:
            return False
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    return any(host == suffix or host.endswith("." + suffix) for suffix in ALLOWED_HOSTS)


def _license_name(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


def _usable_commons_license(value: str) -> bool:
    normal = _license_name(value)
    return (
        normal in {"public domain", "cc0", "cc0 1.0"}
        or normal.startswith(("cc by ", "cc by sa "))
        and all(word not in normal.split() for word in ("nc", "nd"))
    )


def _probe_asset(path: Path, mime: str) -> None:
    if mime in IMAGE_MIME_TYPES:
        from PIL import Image

        try:
            with Image.open(path) as image:
                if image.width < 480 or image.height < 270:
                    raise ValueError("Image too small for normalization")
                if Image.MIME.get(image.format) != mime:
                    raise ValueError("The downloaded image type differs from its HTTP content type")
                image.verify()
        except Image.DecompressionBombError as exc:
            raise ValueError("Image exceeds the maximum decoded pixel count") from exc
        return
    with path.open("rb") as stream:
        magic = stream.read(12)
    mp4_header = mime == "video/mp4" and magic[4:8] == b"ftyp"
    webm_header = mime == "video/webm" and magic.startswith(b"\x1a\x45\xdf\xa3")
    if not (mp4_header or webm_header):
        raise ValueError("Downloaded video does not have a supported container header")
    try:
        streams = normalizer.probe(path).get("streams", [])
    except RuntimeError as exc:
        raise ValueError("FFprobe could not read the downloaded video") from exc
    if not any(
        stream.get("codec_type") == "video" and not stream.get("disposition", {}).get("attached_pic")
        and stream.get("width", 0) >= 480 and stream.get("height", 0) >= 270
        for stream in streams
    ):
        raise ValueError("The download does not contain a usable video stream")


class MediaFetcher:
    """Fetch each remote source asset at most once per timeline."""

    def __init__(self, downloads: Path):
        self.downloads = downloads
        self.used_ids: set[tuple[str, str]] = set()
        self.used_digests: set[str] = set()
        self.session = requests.Session()
        self.session.headers["User-Agent"] = os.getenv(
            "ARCHIVE_USER_AGENT", "DocumentaryEngine/1.0 (local documentary media research)"
        )

    def _json(self, url: str, *, params: dict, headers: dict | None = None) -> dict:
        with self.session.get(
            url, params=params, headers=headers, timeout=TIMEOUT, allow_redirects=False
        ) as response:
            if response.status_code != 200:
                raise ValueError(f"Search returned HTTP {response.status_code}")
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Search returned an invalid response")
            return data

    def _wikimedia_commons(self, query: str) -> Iterable[Candidate]:
        data = self._json(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query", "format": "json", "formatversion": 2,
                "generator": "search", "gsrnamespace": 6, "gsrlimit": 10, "gsrsearch": query,
                "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata",
                "iiurlwidth": 1280,
                "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|ObjectName",
            },
        )
        pages = sorted(data.get("query", {}).get("pages", []), key=lambda page: page.get("index", 999))
        for page in pages:
            for image in page.get("imageinfo", []):
                metadata = image.get("extmetadata", {})
                license_name = metadata.get("LicenseShortName", {}).get("value", "")
                if not _usable_commons_license(license_name) or image.get("mime") not in IMAGE_MIME_TYPES:
                    continue
                yield Candidate(
                    "wikimedia_commons", str(page["pageid"]), image.get("thumburl") or image.get("url", ""),
                    image.get("descriptionurl", ""), license_name,
                    metadata.get("LicenseUrl", {}).get("value", ""),
                    # Commons artist fields can contain attribution links and HTML.
                    unescape(metadata.get("Artist", {}).get("value", "")),
                    page.get("title", ""),
                )

    def _openverse(self, query: str) -> Iterable[Candidate]:
        data = self._json(
            "https://api.openverse.org/v1/images/",
            params={"q": query, "page_size": 10, "license": "cc0,pdm,by,by-sa", "mature": "false"},
        )
        for image in data.get("results", []):
            license_id = image.get("license", "")
            if license_id not in {"cc0", "pdm", "by", "by-sa"}:
                continue
            yield Candidate(
                "openverse", str(image["id"]), image.get("url", ""),
                image.get("foreign_landing_url", ""),
                f"{license_id} {image.get('license_version') or ''}".strip(),
                image.get("license_url", ""), image.get("creator") or "", image.get("title") or "",
            )

    def _pexels_stock(self, query: str) -> Iterable[Candidate]:
        api_key = os.getenv("PEXELS_API_KEY")
        if not api_key:
            return
        headers = {"Authorization": api_key}
        data = self._json(
            "https://api.pexels.com/v1/videos/search",
            params={"query": query, "orientation": "landscape", "per_page": 8},
            headers=headers,
        )
        for item in data.get("videos", []):
            files = [
                file for file in item.get("video_files", [])
                if file.get("file_type") == "video/mp4" and 720 <= (file.get("width") or 0) <= 1920
            ]
            if not files:
                continue
            video = max(files, key=lambda file: file["width"])
            yield Candidate(
                "pexels_stock", f"video:{item['id']}", video.get("link", ""), item.get("url", ""),
                "Pexels License", "https://www.pexels.com/license/", item.get("user", {}).get("name", ""),
                kind="video",
            )
        data = self._json(
            "https://api.pexels.com/v1/search",
            params={"query": query, "orientation": "landscape", "per_page": 8},
            headers=headers,
        )
        for item in data.get("photos", []):
            yield Candidate(
                "pexels_stock", f"photo:{item['id']}", item.get("src", {}).get("large2x", ""),
                item.get("url", ""), "Pexels License", "https://www.pexels.com/license/",
                item.get("photographer", ""), item.get("alt", ""),
            )

    def _pixabay(self, query: str) -> Iterable[Candidate]:
        api_key = os.getenv("PIXABAY_API_KEY")
        if not api_key:
            return
        params = {"key": api_key, "q": query[:100], "per_page": 8, "safesearch": "true"}
        data = self._json("https://pixabay.com/api/videos/", params=params)
        license_url = "https://pixabay.com/service/license-summary/"
        for item in data.get("hits", []):
            files = [
                video for video in item.get("videos", {}).values()
                if 720 <= (video.get("width") or 0) <= 1920
            ]
            if not files:
                continue
            yield Candidate(
                "pixabay", f"video:{item['id']}", max(files, key=lambda video: video["width"])["url"],
                item.get("pageURL", ""), "Pixabay Content License", license_url, item.get("user", ""),
                item.get("tags", ""), "video",
            )
        data = self._json(
            "https://pixabay.com/api/",
            params={**params, "image_type": "photo", "orientation": "horizontal"},
        )
        for item in data.get("hits", []):
            yield Candidate(
                "pixabay", f"photo:{item['id']}", item.get("largeImageURL", ""), item.get("pageURL", ""),
                "Pixabay Content License", license_url, item.get("user", ""), item.get("tags", ""),
            )

    def _download(self, candidate: Candidate) -> tuple[Path, dict] | None:
        identity = candidate.provider, candidate.asset_id
        if identity in self.used_ids or not _allowed_download(candidate.download):
            return None
        supported = VIDEO_MIME_TYPES if candidate.kind == "video" else IMAGE_MIME_TYPES
        self.downloads.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with self.session.get(
                candidate.download, timeout=TIMEOUT, stream=True, allow_redirects=False
            ) as response:
                if response.status_code != 200:
                    raise ValueError(f"Download returned HTTP {response.status_code}")
                mime = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
                if mime not in supported:
                    raise ValueError("Download returned an unexpected content type")
                length = response.headers.get("Content-Length")
                if length is not None and int(length) > MAX_BYTES:
                    raise ValueError("Download exceeds the asset size limit")
                digest = hashlib.sha256()
                size = 0
                with NamedTemporaryFile(dir=self.downloads, suffix=".part", delete=False) as file:
                    temporary = Path(file.name)
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise ValueError("Download exceeds the asset size limit")
                        digest.update(chunk)
                        file.write(chunk)
            sha256 = digest.hexdigest()
            self.used_ids.add(identity)
            if sha256 in self.used_digests:
                return None
            _probe_asset(temporary, mime)
            destination = self.downloads / f"{sha256}{supported[mime]}"
            temporary.replace(destination)
            self.used_digests.add(sha256)
            return destination, {
                "provider": candidate.provider,
                "asset_id": candidate.asset_id,
                "source_url": candidate.source_url,
                "license": candidate.license,
                "license_url": candidate.license_url,
                "creator": candidate.creator,
                "title": candidate.title,
                "kind": candidate.kind,
                "sha256": sha256,
            }
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def fetch(self, visual: dict) -> tuple[Path, dict] | None:
        """Return a distinct stock asset, reusing only a validated exact-query cache."""
        preferred = visual.get("preferred_source")
        query = visual.get("query")
        if preferred in {"ai_image", "black_screen_card"} or not isinstance(query, str) or not query.strip():
            return None
        query = query.strip()
        filename = hashlib.sha256(json.dumps([preferred, query], ensure_ascii=False).encode()).hexdigest()
        record = self.downloads / f"query-{filename}.json"
        try:
            cached = json.loads(record.read_text(encoding="utf-8"))
            provenance = cached["provenance"]
            name = cached["file"]
            identity = provenance["provider"], provenance["asset_id"]
            if Path(name).name == name and identity not in self.used_ids:
                path = self.downloads / name
                with path.open("rb") as fp:
                    digest = hashlib.file_digest(fp, "sha256").hexdigest()
                if digest == provenance["sha256"] and digest not in self.used_digests:
                    self.used_ids.add(identity)
                    self.used_digests.add(digest)
                    return path, {**provenance, "cache_hit": True}
        except (OSError, ValueError, KeyError, TypeError):
            pass

        providers = sorted(STOCK_PROVIDERS, key=lambda name: name != preferred)
        for provider in providers:
            try:
                for candidate in getattr(self, f"_{provider}")(query):
                    try:
                        asset = self._download(candidate)
                    except (requests.RequestException, ValueError, OSError, SyntaxError) as exc:
                        LOGGER.warning("%s asset skipped (%s)", provider, type(exc).__name__)
                        continue
                    if asset is not None:
                        path, provenance = asset
                        with NamedTemporaryFile(dir=self.downloads, mode="w", encoding="utf-8",
                                                suffix=".json.part", delete=False) as handle:
                            temp = Path(handle.name)
                            json.dump({"file": path.name, "provenance": provenance}, handle)
                        try:
                            temp.replace(record)
                        finally:
                            temp.unlink(missing_ok=True)
                        return path, {**provenance, "cache_hit": False}
            except (requests.RequestException, ValueError, AttributeError, KeyError, TypeError) as exc:
                LOGGER.warning("%s search unavailable (%s)", provider, type(exc).__name__)
        return None


def _pinned_reference(
    root: Path, record: dict, destination: Path, *, asset_directory: str
) -> tuple[Path, dict]:
    """Validate pinned project bytes and fit the complete reference image."""
    from PIL import Image, ImageOps

    if asset_directory not in {"archival", "illustrations"}:
        raise ValueError("Reference asset_directory must be archival or illustrations")
    illustration = asset_directory == "illustrations"
    kind = "Illustration" if illustration else "Archival"
    reference = record.get("path")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError(f"{kind} source needs a file path")
    root = root.resolve()
    asset_root = (root / "assets" / asset_directory).resolve()
    source = (root / reference).resolve()
    if not asset_root.is_relative_to(root) or not source.is_relative_to(asset_root) or not source.is_file():
        raise ValueError(f"{kind} source must be a file under assets/{asset_directory}")
    if source == destination.resolve():
        raise ValueError("Fitted reference destination must differ from the pinned original")
    required = ("provider", "source_url", "title", "creator", "license")
    if any(not isinstance(record.get(field), str) or not record[field].strip() for field in required):
        raise ValueError(f"{kind} source needs complete provenance")
    if illustration and record["provider"] != "original_illustration":
        raise ValueError("Illustration source provider must be original_illustration")
    if record["license"].startswith("CC BY-SA") and not record.get("license_url"):
        raise ValueError("CC BY-SA reference needs its license URL")
    with source.open("rb") as fp:
        digest = hashlib.file_digest(fp, "sha256").hexdigest()
    if digest != record.get("sha256"):
        raise ValueError(f"Pinned {kind.lower()} checksum mismatch")
    with Image.open(source) as original:
        still = ImageOps.exif_transpose(original).convert("RGB")
        fitted = ImageOps.contain(still, (1700, 880), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1920, 1080), (15, 17, 20))
    canvas.paste(fitted, ((1920 - fitted.width) // 2, (1080 - fitted.height) // 2))
    canvas.save(destination, format="PNG")
    provenance = {field: record.get(field, "") for field in (
        "provider", "asset_id", "source_url", "download_url", "license",
        "license_url", "creator", "title", "notes", "display_label")}
    modifications = (
        "Original project-created explanatory graphic; fitted to a dark 16:9 frame and animated with pan or zoom"
        if illustration else "Fitted to a dark 16:9 frame, upscaled and animated with pan or zoom"
    )
    if record["license"].startswith("CC BY-SA"):
        adaptation = "graphic" if illustration else "photograph"
        modifications += f"; adapted {adaptation} retains {record['license']} ({record['license_url']})"
    return destination, {**provenance, "kind": "image", "original_sha256": digest,
                         "modifications": modifications}


def pinned_archival(
    root: Path, record: dict, destination: Path, *, asset_directory: str = "archival"
) -> tuple[Path, dict]:
    """Validate a pinned source and retain the complete reference in frame."""
    return _pinned_reference(root, record, destination, asset_directory=asset_directory)


def pinned_illustration(root: Path, record: dict, destination: Path) -> tuple[Path, dict]:
    """Fit a checksum-pinned original explanatory illustration with its provenance."""
    return _pinned_reference(root, record, destination, asset_directory="illustrations")
