import io
import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


class FetchError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class FetchedPage:
    url: str
    title: str
    text: str
    content_type: str


BLOCKED_HOSTS = {
    "localhost",
    "searxng",
    "ollama",
    "backend",
    "db",
    "frontend",
    "research-worker",
    "host.docker.internal",
    "gateway.docker.internal",
}
BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".docker")
MAX_TEXT_CHARS = 20000


def _hostname_is_blocked(hostname):
    host = hostname.rstrip(".").lower()
    if host in BLOCKED_HOSTS:
        return True
    return any(host.endswith(suffix) for suffix in BLOCKED_SUFFIXES)


def validate_public_url(url, allowed_ports):
    try:
        parsed = urlsplit(url)
    except ValueError:
        raise FetchError("invalid_url")
    if parsed.scheme not in {"http", "https"}:
        raise FetchError("unsupported_scheme")
    if parsed.username or parsed.password:
        raise FetchError("credentials_not_allowed")
    hostname = parsed.hostname
    if not hostname:
        raise FetchError("missing_hostname")
    if _hostname_is_blocked(hostname):
        raise FetchError("blocked_hostname")
    try:
        port = parsed.port
    except ValueError:
        raise FetchError("invalid_port")
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    if allowed_ports and port not in allowed_ports:
        raise FetchError("blocked_port")

    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None:
        if not literal.is_global:
            raise FetchError("blocked_address")
        return hostname, port

    try:
        ascii_host = hostname.encode("idna").decode("ascii")
        addresses = socket.getaddrinfo(
            ascii_host, port, type=socket.SOCK_STREAM
        )
    except (UnicodeError, OSError):
        raise FetchError("dns_error")
    if not addresses:
        raise FetchError("dns_error")
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address[4][0])
        except ValueError:
            raise FetchError("dns_error")
        if not ip.is_global:
            raise FetchError("blocked_address")
    return hostname, port


def _decode_bytes(data, content_type):
    charset = "utf-8"
    match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type or "")
    if match:
        charset = match.group(1)
    try:
        return data.decode(charset, errors="replace")
    except LookupError:
        return data.decode("utf-8", errors="replace")


def _extract_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(
        ["script", "style", "noscript", "svg", "nav", "footer", "header", "form", "aside"]
    ):
        tag.decompose()
    title = ""
    if soup.title and soup.title.string:
        title = re.sub(r"\s+", " ", soup.title.string).strip()
    lines = []
    seen = set()
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li", "tr"]):
        text = re.sub(r"\s+", " ", tag.get_text(" ", strip=True)).strip()
        if len(text) < 20:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        lines.append(text)
        if sum(len(line) for line in lines) >= MAX_TEXT_CHARS:
            break
    return title[:512], "\n".join(lines)[:MAX_TEXT_CHARS]


def _extract_pdf(data):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise FetchError("pdf_support_unavailable")
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages[:20]:
            pages.append(page.extract_text() or "")
        text = "\n".join(pages)
    except Exception:
        raise FetchError("pdf_extract_failed")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return "", text[:MAX_TEXT_CHARS]


class SafePageFetcher:
    def __init__(
        self,
        user_agent,
        allowed_ports=None,
        max_html_bytes=3000000,
        max_pdf_bytes=8000000,
        max_redirects=3,
        timeout=(5, 15),
    ):
        self.user_agent = user_agent
        self.allowed_ports = allowed_ports or {80, 443}
        self.max_html_bytes = max_html_bytes
        self.max_pdf_bytes = max_pdf_bytes
        self.max_redirects = max_redirects
        self.timeout = timeout
        self._robots = {}

    def _get(self, url, max_bytes, check_robots):
        current = url
        for _ in range(self.max_redirects + 1):
            validate_public_url(current, self.allowed_ports)
            if check_robots and not self.can_fetch(current):
                raise FetchError("robots_disallowed")
            try:
                response = requests.get(
                    current,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html,application/xhtml+xml,application/pdf,text/plain;q=0.8,*/*;q=0.1",
                    },
                    timeout=self.timeout,
                    allow_redirects=False,
                    stream=True,
                )
            except requests.Timeout:
                raise FetchError("fetch_timeout")
            except requests.RequestException:
                raise FetchError("fetch_unreachable")

            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise FetchError("redirect_without_location")
                current = urljoin(current, location)
                continue
            if response.status_code != 200:
                response.close()
                raise FetchError("http_{0}".format(response.status_code))

            content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            chunks = []
            total = 0
            try:
                for chunk in response.iter_content(8192):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        if content_type == "application/pdf":
                            response.close()
                            raise FetchError("response_too_large")
                        break
                    chunks.append(chunk)
            finally:
                response.close()
            data = b"".join(chunks)
            return current, content_type, data
        raise FetchError("too_many_redirects")

    def can_fetch(self, url):
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        if not host:
            return False
        if host not in self._robots:
            robots_url = "{0}://{1}/robots.txt".format(parsed.scheme, parsed.netloc)
            parser = RobotFileParser()
            try:
                _, content_type, data = self._get(robots_url, 100000, False)
                if content_type.startswith("text/"):
                    parser.parse(_decode_bytes(data, content_type).splitlines())
                else:
                    parser.parse([])
            except FetchError:
                parser.parse([])
            self._robots[host] = parser
        return self._robots[host].can_fetch(self.user_agent, url)

    def fetch(self, url):
        final_url, content_type, data = self._get(
            url, max(self.max_html_bytes, self.max_pdf_bytes), True
        )
        if content_type == "application/pdf" or (
            content_type in {"application/octet-stream", ""}
            and urlsplit(final_url).path.lower().endswith(".pdf")
        ):
            if len(data) > self.max_pdf_bytes:
                raise FetchError("response_too_large")
            title, text = _extract_pdf(data)
            return FetchedPage(final_url, title, text, "application/pdf")
        if content_type not in {
            "text/html",
            "application/xhtml+xml",
            "text/plain",
            "",
        }:
            raise FetchError("unsupported_content_type")
        data = data[: self.max_html_bytes]
        raw = _decode_bytes(data, content_type)
        if content_type == "text/plain":
            title, text = "", re.sub(r"\n{3,}", "\n\n", raw).strip()[:MAX_TEXT_CHARS]
        else:
            title, text = _extract_html(raw)
        return FetchedPage(final_url, title, text, content_type or "text/html")
