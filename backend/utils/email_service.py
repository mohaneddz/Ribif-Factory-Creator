from __future__ import annotations

import base64
import json
import os
import re
import ssl
import time
import imaplib
import smtplib
import threading
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header, make_header
from email.message import EmailMessage
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, make_msgid, parsedate_to_datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
import trafilatura
from dotenv import load_dotenv

from config import EMAIL_CACHE_DIR
from utils.logger import get_logger, task


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = get_logger(__name__)

HEADERS = {"User-Agent": "RIBIF-EmailService/1.0"}
DEFAULT_HTTP_TIMEOUT_S = int(os.getenv("EMAIL_SCRAPE_TIMEOUT_S", "18"))
DEFAULT_SCRAPE_MAX_PAGES = int(os.getenv("EMAIL_SCRAPE_MAX_PAGES", "6"))
DEFAULT_POLL_INTERVAL_S = float(os.getenv("IMAP_POLL_INTERVAL_S", "4.5"))

EMAIL_STATE_PATH = os.getenv("EMAIL_STATE_PATH", str(EMAIL_CACHE_DIR / "imap_state.json"))
FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
    "live.com",
}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
URL_RE = re.compile(r"https?://[^\s\"'<>]+")

ADDRESS_HINTS = (
    "address",
    "headquarters",
    "hq",
    "office",
    "located at",
    "location",
)

ADDRESS_RE = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9.,' -]{3,}\b"
    r"(Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Place|Pl|Suite|Ste|Floor|Fl|Building|Bldg|Parkway|Pkwy)\b",
    re.IGNORECASE,
)

SOCIAL_DOMAINS = {
    "linkedin.com": "linkedin",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "github.com": "github",
    "youtube.com": "youtube",
    "tiktok.com": "tiktok",
}

SCRAPE_KEYWORDS = ("about", "contact", "team", "company", "leadership", "management", "press", "careers")

_STATE_LOCK = threading.Lock()


@dataclass
class SMTPConfig:
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    use_tls: bool
    use_ssl: bool
    timeout_s: int
    from_address: Optional[str]


@dataclass
class IMAPConfig:
    host: str
    port: int
    username: str
    password: str
    use_ssl: bool
    mailbox: str
    timeout_s: int


def _ensure_email_dirs() -> None:
    try:
        EMAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


_ensure_email_dirs()


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if not item:
            continue
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _decode_header_value(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _clean_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).replace("\r", "").strip()


def _split_addresses(value: Optional[str]) -> List[str]:
    if not value:
        return []
    addresses = getaddresses([value])
    return _dedupe([addr for _, addr in addresses if addr])


def _split_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return _dedupe([str(v).strip() for v in value if str(v).strip()])
    if isinstance(value, str):
        parts = re.split(r"[;,]", value)
        return _dedupe([p.strip() for p in parts if p.strip()])
    return [str(value).strip()]


def _normalize_phone(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    if raw.startswith("+"):
        return "+" + re.sub(r"[^\d]", "", raw[1:])
    return re.sub(r"[^\d]", "", raw)


def _load_state() -> Dict[str, Any]:
    path = EMAIL_STATE_PATH
    if not path:
        return {}
    try:
        p = os.path.abspath(path)
        if not os.path.exists(p):
            return {}
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state: Dict[str, Any]) -> None:
    path = EMAIL_STATE_PATH
    if not path:
        return
    try:
        p = os.path.abspath(path)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
    except Exception:
        logger.exception("Failed to persist email state")


def _state_key(cfg: IMAPConfig) -> str:
    return f"{cfg.username}@{cfg.host}:{cfg.mailbox}"


def _flag(value: Any, env_name: str, default: str) -> bool:
    # An explicit False in the payload must win over the env/default
    raw = value if value is not None else (os.getenv(env_name) or default)
    return str(raw).lower() in ("1", "true", "yes")


def _resolve_smtp_config(payload: Dict[str, Any]) -> SMTPConfig:
    host = payload.get("smtp_host") or os.getenv("SMTP_HOST")
    if not host:
        raise ValueError("SMTP host not configured. Set SMTP_HOST or pass smtp_host.")

    port = int(payload.get("smtp_port") or os.getenv("SMTP_PORT") or 587)
    username = payload.get("smtp_username") or os.getenv("SMTP_USERNAME")
    password = payload.get("smtp_password") or os.getenv("SMTP_PASSWORD")
    use_tls = _flag(payload.get("smtp_use_tls"), "SMTP_USE_TLS", "1")
    use_ssl = _flag(payload.get("smtp_use_ssl"), "SMTP_USE_SSL", "0")
    timeout_s = int(payload.get("smtp_timeout_s") or os.getenv("SMTP_TIMEOUT_S") or 25)
    from_address = payload.get("from_address") or os.getenv("SMTP_FROM_ADDRESS") or username
    return SMTPConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        use_tls=use_tls,
        use_ssl=use_ssl,
        timeout_s=timeout_s,
        from_address=from_address,
    )


def _resolve_imap_config(payload: Dict[str, Any]) -> IMAPConfig:
    host = payload.get("imap_host") or os.getenv("IMAP_HOST")
    if not host:
        raise ValueError("IMAP host not configured. Set IMAP_HOST or pass imap_host.")

    port = int(payload.get("imap_port") or os.getenv("IMAP_PORT") or 993)
    username = payload.get("imap_username") or os.getenv("IMAP_USERNAME")
    password = payload.get("imap_password") or os.getenv("IMAP_PASSWORD")
    if not username or not password:
        raise ValueError("IMAP username/password not configured.")
    use_ssl = _flag(payload.get("imap_use_ssl"), "IMAP_USE_SSL", "1")
    mailbox = payload.get("mailbox") or os.getenv("IMAP_MAILBOX") or "INBOX"
    timeout_s = int(payload.get("imap_timeout_s") or os.getenv("IMAP_TIMEOUT_S") or 25)
    return IMAPConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        use_ssl=use_ssl,
        mailbox=mailbox,
        timeout_s=timeout_s,
    )


def _imap_date(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except Exception:
            try:
                dt = parsedate_to_datetime(text)
            except Exception:
                return None
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{dt.day:02d}-{months[dt.month - 1]}-{dt.year}"


def _open_imap(cfg: IMAPConfig) -> imaplib.IMAP4:
    if cfg.use_ssl:
        client = imaplib.IMAP4_SSL(cfg.host, cfg.port, timeout=cfg.timeout_s)
    else:
        client = imaplib.IMAP4(cfg.host, cfg.port, timeout=cfg.timeout_s)
    client.login(cfg.username, cfg.password)
    client.select(cfg.mailbox)
    return client


def _build_imap_search(payload: Dict[str, Any]) -> List[str]:
    criteria: List[str] = []
    if payload.get("unseen_only") in (True, "true", "1", 1):
        criteria.append("UNSEEN")
    if payload.get("from_address"):
        criteria.append(f'FROM "{payload.get("from_address")}"')
    if payload.get("to_address"):
        criteria.append(f'TO "{payload.get("to_address")}"')
    if payload.get("subject_contains"):
        criteria.append(f'SUBJECT "{payload.get("subject_contains")}"')
    if payload.get("body_contains"):
        criteria.append(f'BODY "{payload.get("body_contains")}"')
    imap_since = _imap_date(payload.get("since_date"))
    if imap_since:
        criteria.append(f"SINCE {imap_since}")
    if not criteria:
        criteria.append("ALL")
    return criteria


def _decode_payload_bytes(payload_bytes: Optional[bytes], charset: Optional[str]) -> str:
    if not payload_bytes:
        return ""
    if not charset:
        charset = "utf-8"
    try:
        return payload_bytes.decode(charset, errors="replace")
    except Exception:
        try:
            return payload_bytes.decode("utf-8", errors="replace")
        except Exception:
            return payload_bytes.decode(errors="replace")


def _parse_email_message(msg_bytes: bytes, include_body: bool = True, include_attachments: bool = False) -> Dict[str, Any]:
    parser = BytesParser(policy=policy.default)
    msg = parser.parsebytes(msg_bytes)

    subject = _decode_header_value(msg.get("subject"))
    from_addr = _decode_header_value(msg.get("from"))
    to_addr = _decode_header_value(msg.get("to"))
    cc_addr = _decode_header_value(msg.get("cc"))
    date_raw = msg.get("date")
    message_id = _decode_header_value(msg.get("message-id"))

    date_iso = None
    if date_raw:
        try:
            date_iso = parsedate_to_datetime(date_raw).isoformat()
        except Exception:
            date_iso = None

    body_text = ""
    body_html = ""
    attachments: List[Dict[str, Any]] = []

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition = (part.get_content_disposition() or "").lower()

        if content_type == "text/plain" and include_body and not body_text:
            body_text = _decode_payload_bytes(part.get_payload(decode=True), part.get_content_charset())
            continue
        if content_type == "text/html" and include_body and not body_html:
            body_html = _decode_payload_bytes(part.get_payload(decode=True), part.get_content_charset())
            continue

        if disposition in ("attachment", "inline") or part.get_filename():
            filename = _decode_header_value(part.get_filename()) or "attachment"
            payload = part.get_payload(decode=True) or b""
            attachment = {
                "filename": filename,
                "content_type": content_type,
                "size_bytes": len(payload),
                "content_id": part.get("content-id"),
            }
            if include_attachments:
                attachment["content_base64"] = base64.b64encode(payload).decode("utf-8")
            attachments.append(attachment)

    return {
        "message_id": message_id,
        "date": date_iso,
        "subject": subject,
        "from": from_addr,
        "to": to_addr,
        "cc": cc_addr,
        "from_addresses": _split_addresses(from_addr),
        "to_addresses": _split_addresses(to_addr),
        "cc_addresses": _split_addresses(cc_addr),
        "body_text": _clean_text(body_text),
        "body_html": _clean_text(body_html),
        "attachments": attachments,
    }


def send_email(payload: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _resolve_smtp_config(payload)
    to_list = _split_list(payload.get("to"))
    if not to_list:
        raise ValueError("Missing recipient list (to).")

    subject = _clean_text(payload.get("subject")) or "(no subject)"
    text_body = payload.get("text")
    html_body = payload.get("html")
    if not text_body and not html_body:
        raise ValueError("Provide text or html body.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.from_address or cfg.username or "no-reply@example.com"
    msg["To"] = ", ".join(to_list)
    cc_list = _split_list(payload.get("cc"))
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    bcc_list = _split_list(payload.get("bcc"))
    reply_to = _clean_text(payload.get("reply_to"))
    if reply_to:
        msg["Reply-To"] = reply_to
    msg_id = make_msgid()
    msg["Message-Id"] = msg_id

    if text_body and html_body:
        msg.set_content(str(text_body))
        msg.add_alternative(str(html_body), subtype="html")
    elif html_body:
        msg.add_alternative(str(html_body), subtype="html")
    else:
        msg.set_content(str(text_body))

    attachments = payload.get("attachments") or []
    if isinstance(attachments, dict):
        attachments = [attachments]
    for item in attachments:
        if not isinstance(item, dict):
            continue
        filename = item.get("filename") or "attachment"
        content_type = item.get("content_type") or "application/octet-stream"
        content_b64 = item.get("content_base64")
        raw_bytes = None
        if content_b64:
            try:
                raw_bytes = base64.b64decode(content_b64)
            except Exception:
                raw_bytes = None
        if raw_bytes is None and item.get("path"):
            try:
                raw_bytes = open(item["path"], "rb").read()
            except Exception:
                raw_bytes = None
        if raw_bytes is None:
            continue
        maintype, subtype = content_type.split("/", 1) if "/" in content_type else (content_type, "octet-stream")
        msg.add_attachment(raw_bytes, maintype=maintype, subtype=subtype, filename=filename)

    recipients = list(to_list)
    recipients.extend(cc_list)
    recipients.extend(bcc_list)

    with task("email.send", logger):
        if cfg.use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=cfg.timeout_s, context=context) as server:
                if cfg.username and cfg.password:
                    server.login(cfg.username, cfg.password)
                server.send_message(msg, from_addr=msg["From"], to_addrs=recipients)
        else:
            with smtplib.SMTP(cfg.host, cfg.port, timeout=cfg.timeout_s) as server:
                if cfg.use_tls:
                    server.starttls(context=ssl.create_default_context())
                if cfg.username and cfg.password:
                    server.login(cfg.username, cfg.password)
                server.send_message(msg, from_addr=msg["From"], to_addrs=recipients)

    return {
        "status": "sent",
        "message_id": msg_id.strip("<>"),
        "smtp_host": cfg.host,
        "smtp_port": cfg.port,
        "recipients": recipients,
        "subject": subject,
    }


def poll_inbox(payload: Dict[str, Any], write_state: bool = True) -> Dict[str, Any]:
    cfg = _resolve_imap_config(payload)
    include_body = payload.get("include_body") not in (False, "false", "0", 0)
    include_attachments = payload.get("include_attachments") in (True, "true", "1", 1)
    limit = payload.get("limit")
    mark_seen = payload.get("mark_seen") in (True, "true", "1", 1)

    state_key = _state_key(cfg)
    since_uid = payload.get("since_uid")

    with _STATE_LOCK:
        state = _load_state()
        if since_uid is None:
            since_uid = state.get(state_key)

    with task("email.imap_search", logger):
        client = _open_imap(cfg)
        try:
            criteria = _build_imap_search(payload)
            status, data = client.uid("search", None, " ".join(criteria))
            if status != "OK":
                raise RuntimeError(f"IMAP search failed: {status}")
            raw = data[0] or b""
            uids = [int(x) for x in raw.split() if x.isdigit()]
            if since_uid is not None:
                try:
                    since_val = int(since_uid)
                    uids = [uid for uid in uids if uid > since_val]
                except Exception:
                    pass
            if limit:
                try:
                    limit_val = int(limit)
                    uids = uids[-limit_val:]
                except Exception:
                    pass

            emails: List[Dict[str, Any]] = []
            latest_uid = None

            for uid in uids:
                status, msg_data = client.uid("fetch", str(uid), "(RFC822)")
                if status != "OK" or not msg_data:
                    continue
                msg_bytes = msg_data[0][1]
                parsed = _parse_email_message(msg_bytes, include_body=include_body, include_attachments=include_attachments)
                parsed["uid"] = uid
                emails.append(parsed)
                latest_uid = max(latest_uid or uid, uid)
                if mark_seen:
                    try:
                        client.uid("store", str(uid), "+FLAGS", "(\\Seen)")
                    except Exception:
                        pass
        finally:
            try:
                client.logout()
            except Exception:
                pass

    if write_state and latest_uid is not None:
        with _STATE_LOCK:
            state = _load_state()
            state[state_key] = latest_uid
            _save_state(state)

    return {
        "status": "ok",
        "count": len(emails),
        "latest_uid": latest_uid,
        "state_key": state_key,
        "emails": emails,
        "criteria": _build_imap_search(payload),
    }


def watch_inbox(payload: Dict[str, Any]) -> Dict[str, Any]:
    timeout_s = float(payload.get("timeout_s") or 25)
    poll_interval = float(payload.get("poll_interval_s") or DEFAULT_POLL_INTERVAL_S)
    start = time.time()
    polls = 0
    latest_uid = None
    state_key = None

    while (time.time() - start) < timeout_s:
        polls += 1
        result = poll_inbox(payload, write_state=False)
        state_key = result.get("state_key")
        latest_uid = result.get("latest_uid")
        if result.get("emails"):
            if latest_uid is not None and state_key:
                with _STATE_LOCK:
                    state = _load_state()
                    state[state_key] = latest_uid
                    _save_state(state)
            result["status"] = "found"
            result["elapsed_s"] = round(time.time() - start, 2)
            result["polls"] = polls
            return result
        time.sleep(poll_interval)

    return {
        "status": "timeout",
        "elapsed_s": round(time.time() - start, 2),
        "polls": polls,
        "latest_uid": latest_uid,
        "state_key": state_key,
        "emails": [],
    }


def _fetch_url(url: str, timeout_s: int = DEFAULT_HTTP_TIMEOUT_S) -> Tuple[str, str]:
    resp = requests.get(url, headers=HEADERS, timeout=timeout_s)
    resp.raise_for_status()
    return resp.text, resp.url


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.scheme:
        parsed = parsed._replace(scheme="https")
    return urlunparse(parsed._replace(fragment=""))


def _same_domain(base_url: str, target_url: str) -> bool:
    try:
        return urlparse(base_url).netloc.lower() == urlparse(target_url).netloc.lower()
    except Exception:
        return False


def _score_link(url: str) -> int:
    u = url.lower()
    return sum(1 for k in SCRAPE_KEYWORDS if k in u)


def _extract_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a.get("href") or ""
        if href.startswith("mailto:") or href.startswith("tel:") or href.startswith("javascript:"):
            continue
        link = urljoin(base_url, href)
        link = _normalize_url(link)
        if link and link.startswith("http"):
            links.append(link)
    return _dedupe(links)


def _extract_json_ld_org(soup: BeautifulSoup) -> Dict[str, Any]:
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("@type", "")).lower()
            if item_type in ("organization", "corporation", "localbusiness", "company"):
                return item
    return {}


def _extract_meta(soup: BeautifulSoup) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    title_tag = soup.find("title")
    if title_tag and title_tag.text:
        meta["title"] = _clean_text(title_tag.text)
    for name in ("description", "keywords"):
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            meta[name] = _clean_text(tag.get("content"))
    for prop in ("og:site_name", "og:title", "og:description", "og:url"):
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            meta[prop] = _clean_text(tag.get("content"))
    return meta


def _extract_contacts_from_text(text: str, company_domains: Optional[List[str]] = None) -> Dict[str, Any]:
    text = _clean_text(text)
    emails = EMAIL_RE.findall(text)
    phones = PHONE_RE.findall(text)
    urls = URL_RE.findall(text)

    if company_domains:
        company_domains = [d.lower() for d in company_domains]
        emails = [e for e in emails if e.split("@")[-1].lower() in company_domains]

    phones = [_normalize_phone(p) for p in phones]
    return {
        "emails": _dedupe(emails),
        "phones": _dedupe([p for p in phones if p]),
        "urls": _dedupe(urls),
        "addresses": _dedupe(_extract_address_lines(text)),
    }


def _extract_address_lines(text: str) -> List[str]:
    lines = []
    if not text:
        return lines
    for raw_line in re.split(r"[\n\r]+", text):
        line = raw_line.strip()
        if not line:
            continue
        if any(hint in line.lower() for hint in ADDRESS_HINTS) or ADDRESS_RE.search(line):
            lines.append(line)
    return lines[:8]


def _extract_contacts_from_html(html: str, base_url: Optional[str] = None) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    contacts = _extract_contacts_from_text(text)

    socials: Dict[str, List[str]] = {k: [] for k in SOCIAL_DOMAINS.values()}
    for a in soup.find_all("a", href=True):
        href = a.get("href") or ""
        if href.startswith("mailto:"):
            contacts["emails"].append(href.replace("mailto:", "").strip())
        elif href.startswith("tel:"):
            contacts["phones"].append(_normalize_phone(href.replace("tel:", "")))
        else:
            link = urljoin(base_url or "", href)
            for domain, label in SOCIAL_DOMAINS.items():
                if domain in link:
                    socials[label].append(link)
    contacts["emails"] = _dedupe(contacts["emails"])
    contacts["phones"] = _dedupe([p for p in contacts["phones"] if p])
    contacts["socials"] = {k: _dedupe(v) for k, v in socials.items() if v}
    return contacts


def extract_contacts(payload: Dict[str, Any]) -> Dict[str, Any]:
    text = payload.get("text") or ""
    html = payload.get("html") or ""
    urls = _split_list(payload.get("urls") or payload.get("url"))
    company_domains = _split_list(payload.get("company_domains"))

    contacts: Dict[str, Any] = {"emails": [], "phones": [], "urls": [], "addresses": [], "socials": {}}

    if text:
        with task("contacts.extract_text", logger):
            extracted = _extract_contacts_from_text(text, company_domains or None)
            contacts = _merge_contacts(contacts, extracted)
    if html:
        with task("contacts.extract_html", logger):
            extracted = _extract_contacts_from_html(html)
            contacts = _merge_contacts(contacts, extracted)
    if urls:
        with task("contacts.extract_urls", logger):
            extracted = _extract_contacts_from_urls(urls, company_domains=company_domains)
            contacts = _merge_contacts(contacts, extracted)

    return {
        "status": "ok",
        "contacts": _finalize_contacts(contacts),
    }


def _extract_contacts_from_urls(urls: List[str], company_domains: Optional[List[str]] = None) -> Dict[str, Any]:
    aggregated: Dict[str, Any] = {"emails": [], "phones": [], "urls": [], "addresses": [], "socials": {}}
    for url in urls[:8]:
        try:
            html, final_url = _fetch_url(_normalize_url(url))
            extracted = _extract_contacts_from_html(html, base_url=final_url)
            aggregated = _merge_contacts(aggregated, extracted)
        except Exception:
            continue

    if company_domains:
        company_domains = [d.lower() for d in company_domains]
        emails = [e for e in aggregated.get("emails", []) if e.split("@")[-1].lower() in company_domains]
        aggregated["emails"] = _dedupe(emails)

    return aggregated


def _merge_contacts(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("emails", "phones", "urls", "addresses"):
        base[key] = _dedupe(list(base.get(key, [])) + list(incoming.get(key, [])))
    socials = dict(base.get("socials", {}))
    for key, items in (incoming.get("socials", {}) or {}).items():
        socials[key] = _dedupe(list(socials.get(key, [])) + list(items))
    base["socials"] = socials
    return base


def _finalize_contacts(contacts: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "emails": _dedupe(contacts.get("emails", [])),
        "phones": _dedupe(contacts.get("phones", [])),
        "urls": _dedupe(contacts.get("urls", [])),
        "addresses": _dedupe(contacts.get("addresses", [])),
        "socials": {k: _dedupe(v) for k, v in (contacts.get("socials") or {}).items() if v},
    }


def _extract_company_summary(text: str) -> str:
    if not text:
        return ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return ""
    summary = " ".join(lines[:4])
    return summary[:700]


def _extract_company_name(meta: Dict[str, str], json_ld: Dict[str, Any], fallback: str) -> str:
    for key in ("og:site_name", "title", "og:title"):
        if meta.get(key):
            return meta[key]
    name = json_ld.get("name") if isinstance(json_ld, dict) else None
    if name:
        return str(name)
    return fallback or ""


def _extract_company_details_from_html(html: str, url: str, fallback_name: str = "") -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    meta = _extract_meta(soup)
    json_ld = _extract_json_ld_org(soup)
    text = trafilatura.extract(html) or soup.get_text("\n")

    contacts = _extract_contacts_from_html(html, base_url=url)
    summary = _extract_company_summary(text)

    details = {
        "company_name": _extract_company_name(meta, json_ld, fallback_name),
        "website": url,
        "description": meta.get("description") or meta.get("og:description"),
        "summary": summary,
        "contacts": contacts,
        "meta": meta,
        "json_ld": json_ld if json_ld else None,
    }
    return details


def _crawl_company_site(base_url: str, max_pages: int = DEFAULT_SCRAPE_MAX_PAGES) -> Dict[str, Any]:
    base_url = _normalize_url(base_url)
    if not base_url:
        return {"pages": [], "contacts": {}, "company": {}}

    visited = set()
    queue: List[str] = [base_url]
    pages: List[Dict[str, Any]] = []
    aggregated_contacts: Dict[str, Any] = {"emails": [], "phones": [], "urls": [], "addresses": [], "socials": {}}
    company_details: Dict[str, Any] = {}

    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        try:
            html, final_url = _fetch_url(url)
        except Exception:
            continue

        details = _extract_company_details_from_html(html, final_url, fallback_name=company_details.get("company_name", ""))
        if not company_details:
            company_details = details
        aggregated_contacts = _merge_contacts(aggregated_contacts, details.get("contacts", {}))

        page_entry = {
            "url": final_url,
            "title": details.get("meta", {}).get("title") or "",
            "description": details.get("meta", {}).get("description") or "",
        }
        pages.append(page_entry)

        for link in sorted(_extract_links(html, final_url), key=_score_link, reverse=True):
            if len(pages) + len(queue) >= max_pages:
                break
            if link in visited:
                continue
            if not _same_domain(base_url, link):
                continue
            queue.append(link)

    company_details["contacts"] = _finalize_contacts(aggregated_contacts)
    company_details["pages_scraped"] = len(pages)
    return {
        "company": company_details,
        "contacts": _finalize_contacts(aggregated_contacts),
        "pages": pages,
    }


def _derive_domain_from_emails(emails: List[str]) -> Optional[str]:
    for email_addr in emails:
        if "@" not in email_addr:
            continue
        domain = email_addr.split("@")[-1].lower()
        if domain and domain not in FREE_EMAIL_DOMAINS:
            return domain
    return None


def resolve_company_base_url(payload: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
    candidates: List[str] = []
    website = payload.get("website") or payload.get("url")
    domain = payload.get("domain")
    emails = _split_list(payload.get("emails"))

    if website:
        candidates.append(_normalize_url(str(website)))
    if domain:
        candidates.append(_normalize_url(str(domain)))

    derived_domain = _derive_domain_from_emails(emails)
    if derived_domain:
        candidates.append(_normalize_url(derived_domain))

    candidates = _dedupe([c for c in candidates if c])
    return (candidates[0] if candidates else None), candidates


def scrape_company(payload: Dict[str, Any]) -> Dict[str, Any]:
    base_url, candidates = resolve_company_base_url(payload)
    max_pages = payload.get("max_pages")
    if max_pages is None:
        max_pages = DEFAULT_SCRAPE_MAX_PAGES
    try:
        max_pages = int(max_pages)
    except Exception:
        max_pages = DEFAULT_SCRAPE_MAX_PAGES

    if not base_url:
        return {
            "status": "error",
            "error": "Provide website/domain/emails to resolve a company site.",
            "candidates": candidates,
        }

    with task("company.scrape", logger):
        data = _crawl_company_site(base_url, max_pages=max_pages)

    company_name = payload.get("company_name")
    if company_name and data.get("company"):
        data["company"]["company_name"] = data["company"].get("company_name") or company_name

    data["status"] = "ok"
    data["candidates"] = candidates
    return data
