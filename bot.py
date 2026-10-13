"""Minimal personal Artifact Hell notifier. No Telegram user sign-in required."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import cv2
import numpy as np
import requests

CHANNEL = "LMEvents"
SOURCE = "https://t.me/s/LMEvents"
BASE = Path(__file__).resolve().parent
MAX_AGE_MIN = 58  # skip expired posts, even if the GitHub cron queue is delayed
MAX_IMAGE_BYTES = 5 * 1024 * 1024
THRESHOLD = 0.93
PATTERN = re.compile(r"(?<!\w)#Hell\b", re.I)
PHOTO_PATTERN = re.compile(r"background-image\s*:\s*url\(['\"]?([^)'\"]+)", re.I)
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (compatible; PersonalHellNotifier/1.0)"})


def safe_photo_url(url):
    p = urlparse(url)
    host = (p.hostname or "").lower()
    # Explicit allowlist against SSRF. Fail closed if Telegram changes hosts.
    good = (re.fullmatch(r"cdn\d+\.telesco\.pe", host)
            or re.fullmatch(r"cdn\d*\.telegram-cdn\.org", host)
            or re.fullmatch(r"cdn\d*\.cdn-telegram\.org", host))
    if p.scheme != "https" or not good or p.username or p.password:
        raise ValueError("Unexpected media host; inspect Telegram HTML safely")
    return url


def parse_latest_hell(html, now=None):
    """Only the most recent #Hell in public preview; never scan past pages."""
    now = now or datetime.now(timezone.utc)
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    for node in soup.select("[data-post]"):
        ref = node.get("data-post", "")
        match = re.fullmatch(r"LMEvents/(\d+)", ref, re.I)
        if not match:
            continue
        message_text = node.select_one(".tgme_widget_message_text")
        caption = message_text.get_text(" ", strip=True) if message_text else ""
        if not PATTERN.search(caption):
            continue
        time_tag = node.select_one("time[datetime]")
        if not time_tag:
            continue  # no timestamp = no alert
        try:
            when = datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
            if not when.tzinfo:
                continue
            age = now - when.astimezone(timezone.utc)
        except ValueError:
            continue
        if not timedelta(0) <= age <= timedelta(minutes=MAX_AGE_MIN):
            continue
        photo = node.select_one(".tgme_widget_message_photo_wrap")
        style = photo.get("style", "") if photo else ""
        url_match = PHOTO_PATTERN.search(style)
        if not url_match:
            continue
        try:
            photo_url = safe_photo_url(url_match.group(1).replace("&amp;", "&"))
        except ValueError:
            continue
        mid = int(match.group(1))
        posts.append({"id": mid, "photo": photo_url, "link": f"https://t.me/{CHANNEL}/{mid}", "timestamp": when.isoformat()})
    return max(posts, key=lambda post: post["id"]) if posts else None


def download_image(url):
    safe_photo_url(url)
    with S.get(url, timeout=(10, 20), stream=True, allow_redirects=False) as response:
        if response.status_code != 200:
            raise RuntimeError(f"Image fetch failed (HTTP {response.status_code})")
        data = bytearray()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data) > MAX_IMAGE_BYTES:
                raise RuntimeError("Image too large")
    return bytes(data)


def artifact_score(raw):
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    template = cv2.imread(str(BASE / "artifact_template.png"), cv2.IMREAD_COLOR)
    if image is None or template is None:
        raise RuntimeError("Cannot decode image/template")
    h, w = image.shape[:2]
    if not h or abs(w / h - 500 / 249) > 0.07:
        return 0.0
    image = cv2.resize(image, (500, 249), interpolation=cv2.INTER_AREA)
    upper = image[:69, 155:500]
    match = cv2.matchTemplate(upper, template, cv2.TM_CCOEFF_NORMED)
    return float(np.max(match))


def get_latest():
    response = S.get(SOURCE, timeout=(10, 20), allow_redirects=False)
    if response.status_code != 200:
        raise RuntimeError(f"Channel preview unavailable (HTTP {response.status_code})")
    return parse_latest_hell(response.text)


def send_telegram_photo(raw, caption):
    """Send a JPEG without logging Bot Token, request URL, or API response body."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("Missing Telegram secrets")
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError("Invalid image")
    valid, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not valid:
        raise RuntimeError("JPEG encoding failed")
    try:
        response = S.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": ("hell.jpg", encoded.tobytes(), "image/jpeg")},
            timeout=(10, 25),
        )
    except requests.RequestException:
        raise RuntimeError("Telegram notification request failed (details hidden)") from None
    if response.status_code != 200:
        raise RuntimeError(f"Telegram notification failed (HTTP {response.status_code}; response hidden)")
    try:
        ok = response.json().get("ok")
    except ValueError:
        ok = False
    if not ok:
        raise RuntimeError("Telegram API rejected notification (response hidden)")
    print("Telegram notification delivered")


def notify(post):
    raw = download_image(post["photo"])
    score = artifact_score(raw)
    print(f"Latest #Hell id={post['id']}; icon score={score:.3f}; threshold={THRESHOLD:.2f}")
    if score < THRESHOLD:
        print("Not Artifact Hell. No notification.")
        return
    send_telegram_photo(raw, f"🔔 HELL CỔ VẬT!\n{post['link']}")


def test_notify(file_path):
    """Local fixture only: test icon + real Telegram delivery, without scraping or touching dedupe."""
    raw = Path(file_path).read_bytes()
    score = artifact_score(raw)
    print(f"TEST image icon score={score:.3f}; threshold={THRESHOLD:.2f}")
    if score < THRESHOLD:
        raise RuntimeError("TEST sample did not match Artifact icon")
    send_telegram_photo(raw, "🧪 TEST HELL CỔ VẬT\nĐây là tin nhắn thử nghiệm, KHÔNG phải Hell hiện tại.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["inspect", "notify", "test-image", "test-notify"])
    ap.add_argument("--file", help="Path to latest.json or local test image")
    args = ap.parse_args()
    if args.mode in ("test-image", "test-notify"):
        if not args.file:
            ap.error("--file is required for image tests")
        if args.mode == "test-image":
            print(f"Artifact score = {artifact_score(Path(args.file).read_bytes()):.4f}")
        else:
            test_notify(args.file)
        return
    if args.mode == "inspect":
        post = get_latest()
        if post:
            Path("latest.json").write_text(json.dumps(post), encoding="utf-8")
            # Only digits from Telegram data-post. Avoid injecting untrusted HTML into workflow outputs.
            if os.getenv("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                    f.write(f"post_id={post['id']}\n")
            print(f"Latest active #Hell: {post['id']}")
        else:
            print("No active #Hell found in preview")
        return
    post = json.loads(Path(args.file or "latest.json").read_text(encoding="utf-8"))
    notify(post)


if __name__ == "__main__":
    main()
