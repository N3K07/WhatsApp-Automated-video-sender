from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

from whatsapp_sender import WhatsAppConnectionError, WhatsAppSender

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
STATUS_FILE = BASE_DIR / "status.json"
STOP_FILE = BASE_DIR / "STOP_REQUESTED"

def load_config() -> dict:
    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)

CONFIG = load_config()
TO_SEND = BASE_DIR / CONFIG["folders"]["to_send"]
SENT = BASE_DIR / CONFIG["folders"]["sent"]
LOGS = BASE_DIR / CONFIG["folders"]["logs"]
RECIPIENT = CONFIG["recipient"]
POLL_INTERVAL = CONFIG["automation"]["poll_interval_seconds"]
FILE_STABLE_SECONDS = CONFIG["automation"]["file_stable_seconds"]
MAX_RETRIES = CONFIG["automation"]["max_retries"]
RETRY_DELAY = CONFIG["automation"]["retry_delay_seconds"]
PAGE_TIMEOUT = CONFIG["automation"]["page_timeout_seconds"]
DEBUG_PORT = CONFIG["chrome"]["debug_port"]
VIDEO_EXTENSIONS = {ext.lower() for ext in CONFIG["video_extensions"]}

_current = {"status": "Starting", "current_file": "", "stage": "Starting up", "recipient": RECIPIENT}

def write_status(status: str | None = None, current_file: str | None = None,
                 stage: str | None = None, error: str | None = None) -> None:
    if status is not None:
        _current["status"] = status
    if current_file is not None:
        _current["current_file"] = current_file
    if stage is not None:
        _current["stage"] = stage
    _current["recipient"] = RECIPIENT
    _current["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if error is not None:
        _current["last_error"] = error
    elif status in {"Running", "Stopped", "Idle"}:
        _current.pop("last_error", None)
    temp = STATUS_FILE.with_suffix(".tmp")
    try:
        temp.write_text(json.dumps(_current, indent=2), encoding="utf-8")
        temp.replace(STATUS_FILE)
    except OSError:
        pass

def stop_requested() -> bool:
    return STOP_FILE.exists()

def setup_logging() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(LOGS / "automation.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

def ensure_directories() -> None:
    for folder in (TO_SEND, SENT, LOGS):
        folder.mkdir(parents=True, exist_ok=True)

def find_videos() -> List[Path]:
    videos = [
        p for p in TO_SEND.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
        and not p.name.startswith(".")
    ] if TO_SEND.exists() else []
    return sorted(videos, key=lambda p: p.name.lower())

def wait_until_file_is_stable(path: Path, stable_seconds: int) -> bool:
    logging.info("Waiting for file to finish copying: %s", path.name)
    last_size = -1
    stable_since = None
    while not stop_requested():
        if not path.exists():
            return False
        try:
            current_size = path.stat().st_size
        except OSError:
            time.sleep(1)
            continue
        if current_size == last_size:
            if stable_since is None:
                stable_since = time.monotonic()
            if time.monotonic() - stable_since >= stable_seconds:
                logging.info("File is stable: %s (%d bytes)", path.name, current_size)
                return True
        else:
            last_size = current_size
            stable_since = time.monotonic()
        time.sleep(1)
    return False

def move_to_sent(path: Path) -> Path:
    destination = SENT / path.name
    if destination.exists():
        stamp = time.strftime("%Y%m%d_%H%M%S")
        destination = SENT / f"{path.stem}_{stamp}{path.suffix}"
    shutil.move(str(path), str(destination))
    logging.info("Moved to Sent: %s", destination.name)
    return destination

def process_video(sender: WhatsAppSender, video: Path) -> bool:
    logging.info("==================================================")
    logging.info("Processing: %s", video.name)
    write_status(status="Running", current_file=video.name, stage="Waiting for file to finish copying")
    if not wait_until_file_is_stable(video, FILE_STABLE_SECONDS):
        return False

    for attempt in range(1, MAX_RETRIES + 1):
        if stop_requested():
            return False
        logging.info("Send attempt %d/%d: %s", attempt, MAX_RETRIES, video.name)
        write_status(current_file=video.name, stage=f"Preparing (attempt {attempt}/{MAX_RETRIES})")
        try:
            write_status(stage="Opening recipient chat")
            sender.send_video(video, RECIPIENT)
            write_status(stage="Send operation completed")
            move_to_sent(video)
            logging.info("SUCCESS: %s", video.name)
            write_status(current_file="", stage=f"Sent: {video.name}")
            return True
        except Exception as exc:
            logging.exception("Attempt %d failed for %s: %s", attempt, video.name, exc)
            write_status(current_file=video.name, stage="Send failed", error=str(exc))
            if attempt < MAX_RETRIES and not stop_requested():
                logging.info("Retrying in %d seconds...", RETRY_DELAY)
                write_status(stage=f"Retrying in {RETRY_DELAY} seconds")

                for _ in range(RETRY_DELAY):
                    if stop_requested():
                        return False
                    time.sleep(1)

    logging.error("FAILED: %s", video.name)
    logging.error("The file has NOT been moved and remains in ToSend.")
    write_status(current_file="", stage=f"Failed: {video.name}", error="All send attempts failed")
    return False

def run() -> None:
    setup_logging()
    ensure_directories()
    STOP_FILE.unlink(missing_ok=True)
    write_status(status="Starting", current_file="", stage="Connecting to Chrome/WhatsApp")
    logging.info("==================================================")
    logging.info("WhatsApp automatic video sender starting...")
    logging.info("Recipient: %s", RECIPIENT)
    logging.info("Watching: %s", TO_SEND)
    logging.info("Sent files: %s", SENT)
    logging.info("Chrome debugging port: %s", DEBUG_PORT)
    logging.info("==================================================")

    sender = WhatsAppSender(debug_port=DEBUG_PORT, timeout_seconds=PAGE_TIMEOUT)
    try:
        while not stop_requested():
            try:
                sender.connect()
                sender.wait_until_ready()
                logging.info("WhatsApp Web connection established.")
                write_status(status="Running", stage="Connected; monitoring queue")
                break
            except WhatsAppConnectionError as exc:
                logging.error("WhatsApp connection failed: %s", exc)
                write_status(status="Waiting for connection", stage="Open Chrome and WhatsApp Web", error=str(exc))
                for _ in range(10):
                    if stop_requested():
                        break
                    time.sleep(1)

        while not stop_requested():
            videos = find_videos()
            if videos:
                logging.info("Found %d video(s) waiting to be sent.", len(videos))
                for video in videos:
                    if stop_requested():
                        break
                    if video.exists():
                        process_video(sender, video)


                        if stop_requested():
                            break
                        time.sleep(2)
            else:
                write_status(status="Running", current_file="", stage="Monitoring queue")
                logging.info("No videos found. Waiting...")
            for _ in range(POLL_INTERVAL):
                if stop_requested():
                    break
                time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping automation...")
    except Exception as exc:
        logging.exception("Fatal automation error: %s", exc)
        write_status(status="Error", stage="Automation stopped due to an error", error=str(exc))
    finally:
        try:
            sender.close()
        except Exception:
            logging.exception("Could not close the WhatsApp connection cleanly.")
        STOP_FILE.unlink(missing_ok=True)
        if _current.get("status") == "Error":
            write_status(current_file="", stage="Automation ended after an error")
        else:
            write_status(status="Stopped", current_file="", stage="Automation stopped")
        logging.info("Automation stopped.")

if __name__ == "__main__":
    run()
