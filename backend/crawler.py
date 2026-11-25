from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup

SKIP_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".pdf", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".wav",
    ".css", ".js", ".json", ".xml", ".woff", ".woff2", ".ttf"
)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def normalize_url(base_url: str, raw_link: str) -> str | None:
    if not raw_link:
        return None

    raw_link = raw_link.strip()
    lowered = raw_link.lower()
    if lowered.startswith(("mailto:", "tel:", "javascript:", "data:", "blob:")):
        return None

    joined = urljoin(base_url, raw_link)
    clean_url, _ = urldefrag(joined)
    parsed = urlparse(clean_url)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None

    path_lower = parsed.path.lower()
    if any(path_lower.endswith(ext) for ext in SKIP_EXTENSIONS):
        return None

    # Normalisasi host ke lowercase dan hapus trailing slash kecuali root '/'
    netloc = parsed.netloc.lower()
    path = parsed.path if parsed.path else "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    normalized = parsed._replace(scheme=parsed.scheme.lower(), netloc=netloc, path=path)
    return normalized.geturl()


def crawl_website(
    start_url: str,
    max_depth: int = 2,
    max_pages: int = 250,
    max_links_per_page: int = 40,
    timeout: float = 5.0,
) -> dict:
    """
    Melakukan crawling mulai dari start_url hingga kedalaman max_depth.
    Mengembalikan nodes, edges, serta catatan error/statistik agar tetap aman untuk URL bebas.
    """
    seed = normalize_url("", start_url)
    if not seed:
        raise ValueError("URL awal tidak valid. Pastikan menggunakan format http:// atau https://.")

    max_depth = max(0, min(int(max_depth), 5))
    max_pages = max(1, min(int(max_pages), 1000))

    visited_html: set[str] = set()
    discovered_nodes: dict[str, dict] = {
        seed: {"id": seed, "label": seed, "depth": 0, "status": "queued"}
    }
    edges: list[tuple[str, str]] = []
    edge_set: set[tuple[str, str]] = set()
    errors: list[dict] = []

    queue: deque[tuple[str, int]] = deque([(seed, 0)])
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    while queue and len(visited_html) < max_pages:
        current_url, current_depth = queue.popleft()

        if current_url in visited_html:
            continue
        if current_depth > max_depth:
            continue

        visited_html.add(current_url)

        try:
            response = session.get(current_url, timeout=timeout, allow_redirects=True)
            content_type = response.headers.get("Content-Type", "").lower()

            # Gunakan URL akhir setelah redirect jika valid
            final_url = normalize_url("", response.url) or current_url
            if final_url != current_url and final_url not in discovered_nodes:
                discovered_nodes[final_url] = {
                    "id": final_url,
                    "label": final_url,
                    "depth": current_depth,
                    "status": "redirected",
                }
                pair = (current_url, final_url)
                if pair not in edge_set:
                    edge_set.add(pair)
                    edges.append(pair)

            discovered_nodes[current_url]["status"] = f"HTTP {response.status_code}"

            if response.status_code >= 400:
                errors.append({"url": current_url, "reason": f"HTTP {response.status_code}"})
                continue

            if "text/html" not in content_type and "xhtml" not in content_type:
                continue

            # Jika sudah mencapai batas kedalaman, tidak perlu mengekstrak link keluar lagi
            if current_depth >= max_depth:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            extracted_count = 0

            for anchor in soup.find_all("a", href=True):
                if extracted_count >= max_links_per_page:
                    break

                target_url = normalize_url(response.url, anchor["href"])
                if not target_url or target_url == current_url:
                    continue

                pair = (current_url, target_url)
                if pair not in edge_set:
                    edge_set.add(pair)
                    edges.append(pair)
                    extracted_count += 1

                next_depth = current_depth + 1
                if target_url not in discovered_nodes:
                    discovered_nodes[target_url] = {
                        "id": target_url,
                        "label": target_url,
                        "depth": next_depth,
                        "status": "discovered",
                    }
                    if len(discovered_nodes) <= max_pages * 4:
                        queue.append((target_url, next_depth))
                else:
                    # Simpan kedalaman terkecil jika URL ditemukan lewat jalur yang lebih dekat
                    if next_depth < discovered_nodes[target_url]["depth"]:
                        discovered_nodes[target_url]["depth"] = next_depth

        except requests.exceptions.Timeout:
            discovered_nodes[current_url]["status"] = "timeout"
            errors.append({"url": current_url, "reason": "Request timeout"})
        except requests.exceptions.RequestException as exc:
            discovered_nodes[current_url]["status"] = "error"
            errors.append({"url": current_url, "reason": str(exc)})

    session.close()

    return {
        "seed_url": seed,
        "max_depth": max_depth,
        "nodes": list(discovered_nodes.values()),
        "edges": [{"from": src, "to": dst} for src, dst in edges],
        "crawled_pages_count": len(visited_html),
        "total_nodes": len(discovered_nodes),
        "total_edges": len(edges),
        "errors": errors[:30],
    }
