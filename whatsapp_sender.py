from __future__ import annotations

import ctypes
import logging
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import (
    Browser,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


class WhatsAppError(Exception):
    pass


class WhatsAppConnectionError(WhatsAppError):
    pass


class RecipientNotFoundError(WhatsAppError):
    pass


class VideoSendError(WhatsAppError):
    pass


user32 = ctypes.windll.user32

EnumWindowsProc = ctypes.WINFUNCTYPE(
    ctypes.c_bool,
    ctypes.c_void_p,
    ctypes.c_void_p,
)

WM_CLOSE = 0x0010


def _get_window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _get_class_name(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def close_persistent_windows_dialogs() -> int:


    closed = 0

    titles = {
        "open",
        "save as",
        "select a file",
        "choose a file",
        "file upload",
        "upload",
    }

    def callback(hwnd, _lparam):
        nonlocal closed

        if not user32.IsWindowVisible(hwnd):
            return True

        class_name = _get_class_name(hwnd)
        title = _get_window_text(hwnd).strip()
        normalized = title.lower()


        if class_name == "#32770":
            if (
                normalized in titles
                or "open" in normalized
                or "select" in normalized
                or "choose" in normalized
                or "upload" in normalized
            ):
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                closed += 1

        return True

    user32.EnumWindows(
        EnumWindowsProc(callback),
        0,
    )

    if closed:
        logging.info(
            "Closed %d persistent Windows file dialog(s).",
            closed,
        )
        time.sleep(0.5)

    return closed


class WhatsAppSender:
    def __init__(
        self,
        debug_port: int = 9222,
        timeout_seconds: int = 30,
    ):
        self.debug_port = debug_port
        self.timeout_ms = timeout_seconds * 1000

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None


    def connect(self) -> None:
        if self.browser is not None:
            return

        try:
            self.playwright = sync_playwright().start()

            self.browser = self.playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{self.debug_port}"
            )

        except Exception as exc:
            self.close()
            raise WhatsAppConnectionError(
                f"Could not connect to Chrome on port "
                f"{self.debug_port}: {exc}"
            ) from exc

        pages = []

        for context in self.browser.contexts:
            pages.extend(context.pages)

        if not pages:
            raise WhatsAppConnectionError(
                "Chrome is connected, but no browser tab was found."
            )

        whatsapp_pages = [
            page
            for page in pages
            if "web.whatsapp.com" in page.url.lower()
        ]

        self.page = (
            whatsapp_pages[0]
            if whatsapp_pages
            else pages[0]
        )

        logging.info(
            "Connected to Chrome. Current URL: %s",
            self.page.url,
        )


    def wait_until_ready(self) -> None:
        if self.page is None:
            raise WhatsAppConnectionError(
                "WhatsApp page is not connected."
            )

        deadline = time.monotonic() + (
            self.timeout_ms / 1000
        )

        while time.monotonic() < deadline:
            try:
                if "web.whatsapp.com" not in self.page.url.lower():
                    self._find_whatsapp_page()


                selectors = [
                    'div[contenteditable="true"][data-tab]',
                    'div[contenteditable="true"][role="textbox"]',
                    'input[placeholder*="Search"]',
                    'div[aria-label*="Search"]',
                ]

                for selector in selectors:
                    try:
                        if self.page.locator(selector).first.is_visible(
                            timeout=1000
                        ):
                            logging.info(
                                "WhatsApp Web appears ready."
                            )
                            return
                    except Exception:
                        pass

            except Exception:
                pass

            time.sleep(1)

        raise WhatsAppConnectionError(
            "WhatsApp Web did not become ready within the timeout."
        )

    def _find_whatsapp_page(self) -> None:
        if self.browser is None:
            raise WhatsAppConnectionError(
                "Browser is not connected."
            )

        for context in self.browser.contexts:
            for page in context.pages:
                if "web.whatsapp.com" in page.url.lower():
                    self.page = page
                    return

        raise WhatsAppConnectionError(
            "No WhatsApp Web tab was found."
        )


    def _get_visible_textboxes(self):
        if self.page is None:
            return []

        boxes = []
        selectors = [
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
            'input[type="text"]',
            'input[placeholder*="Search"]',
        ]

        seen = set()

        for selector in selectors:
            try:
                locators = self.page.locator(selector)
                count = locators.count()

                for index in range(count):
                    locator = locators.nth(index)

                    try:
                        if not locator.is_visible(timeout=300):
                            continue


                        key = (selector, index)

                        if key not in seen:
                            seen.add(key)
                            boxes.append(locator)
                    except Exception:
                        pass
            except Exception:
                pass

        return boxes

    def _find_search_box(self):


        if self.page is None:
            return None

        selectors = [
            'div[contenteditable="true"][data-tab="3"]',
            'div[contenteditable="true"][aria-label*="Search"]',
            'div[contenteditable="true"][aria-placeholder*="Search"]',
            'input[placeholder*="Search"]',
            'input[aria-label*="Search"]',
        ]

        for selector in selectors:
            try:
                locators = self.page.locator(selector)
                count = locators.count()

                for index in range(count):
                    locator = locators.nth(index)

                    try:
                        if locator.is_visible(timeout=500):
                            return locator
                    except Exception:
                        pass
            except Exception:
                pass


        for locator in self._get_visible_textboxes():
            try:
                aria = (
                    locator.get_attribute("aria-label")
                    or ""
                ).lower()

                placeholder = (
                    locator.get_attribute("aria-placeholder")
                    or ""
                ).lower()

                data_tab = (
                    locator.get_attribute("data-tab")
                    or ""
                )

                if (
                    "search" in aria
                    or "search" in placeholder
                    or data_tab == "3"
                ):
                    return locator
            except Exception:
                pass

        return None

    def _message_composer_visible(self) -> bool:
        if self.page is None:
            return False

        selectors = [
            'footer div[contenteditable="true"]',
            'div[contenteditable="true"][data-tab="10"]',
            'div[contenteditable="true"][aria-placeholder*="message"]',
            'div[contenteditable="true"][aria-label*="message"]',
        ]

        for selector in selectors:
            try:
                if self.page.locator(selector).first.is_visible(
                    timeout=300
                ):
                    return True
            except Exception:
                pass

        return False

    def _chat_header_matches(self, recipient: str) -> bool:
        if self.page is None:
            return False

        recipient_normalized = " ".join(
            recipient.lower().split()
        )


        header_selectors = [
            'header',
            '[data-testid="conversation-header"]',
            '[data-testid="conversation-info-header"]',
            'div[role="main"] header',
        ]

        for selector in header_selectors:
            try:
                headers = self.page.locator(selector)
                count = headers.count()

                for index in range(count):
                    header = headers.nth(index)

                    if not header.is_visible(timeout=300):
                        continue

                    text = " ".join(
                        header.inner_text(
                            timeout=500
                        ).split()
                    ).lower()

                    if recipient_normalized in text:
                        return True
            except Exception:
                pass


        try:
            main = self.page.locator(
                'div[role="main"]'
            ).first

            if main.is_visible(timeout=500):
                text = " ".join(
                    main.inner_text(
                        timeout=1000
                    ).split()
                ).lower()


                if (
                    recipient_normalized in text
                    and self._message_composer_visible()
                ):
                    return True
        except Exception:
            pass

        return False

    def _return_to_chat_list(self) -> None:


        if self.page is None:
            return

        logging.info(
            "Resetting WhatsApp to chat/search state..."
        )


        for _ in range(2):
            try:
                self.page.keyboard.press("Escape")
                time.sleep(0.25)
            except Exception:
                pass


        self._close_native_dialogs()


        back_selectors = [
            'button[aria-label*="Back"]',
            'div[role="button"][aria-label*="Back"]',
            '[data-testid="back"]',
        ]

        for selector in back_selectors:
            try:
                locator = self.page.locator(
                    selector
                ).first

                if locator.is_visible(timeout=500):
                    locator.click()
                    time.sleep(0.5)
                    break
            except Exception:
                pass


        search_button_selectors = [
            'button[aria-label*="Search"]',
            'div[role="button"][aria-label*="Search"]',
            '[data-testid="chat-list-search"]',
        ]

        if self._find_search_box() is None:
            for selector in search_button_selectors:
                try:
                    locator = self.page.locator(
                        selector
                    ).first

                    if locator.is_visible(timeout=500):
                        locator.click()
                        time.sleep(0.5)
                        break
                except Exception:
                    pass

    def _clear_search_box(self, search_box) -> None:
        try:
            search_box.click()
            search_box.press("Control+A")
            search_box.press("Backspace")
            time.sleep(0.2)
        except Exception:
            pass

    def _verify_chat_open(
        self,
        recipient: str,
    ) -> None:
        if self.page is None:
            raise RecipientNotFoundError(
                "WhatsApp page is not connected."
            )

        deadline = time.monotonic() + 8

        while time.monotonic() < deadline:
            if self._chat_header_matches(recipient):
                logging.info(
                    "Verified recipient chat is open: %s",
                    recipient,
                )
                return

            time.sleep(0.3)

        raise RecipientNotFoundError(
            f"WhatsApp did not verify that the '{recipient}' chat was open."
        )

    def open_recipient(self, recipient: str) -> None:
        if self.page is None:
            raise WhatsAppConnectionError(
                "WhatsApp page is not connected."
            )

        self.wait_until_ready()

        logging.info(
            "Preparing recipient chat: %s",
            recipient,
        )


        self._return_to_chat_list()

        search_box = self._find_search_box()

        if search_box is None:
            raise RecipientNotFoundError(
                "WhatsApp chat-list search box was not found. "
                "Refusing to type the recipient into the message composer."
            )

        logging.info(
            "Chat-list search box confirmed. Searching for: %s",
            recipient,
        )

        try:
            self._clear_search_box(search_box)
            search_box.click()
            search_box.fill(recipient)
        except Exception as exc:
            raise RecipientNotFoundError(
                f"Could not enter recipient into the WhatsApp search box: {exc}"
            ) from exc

        time.sleep(1.2)


        result_selectors = [
            f'[title="{recipient}"]',
            f'[aria-label="{recipient}"]',
        ]

        for selector in result_selectors:
            try:
                locator = self.page.locator(
                    selector
                ).last

                if locator.is_visible(timeout=1200):
                    locator.click()
                    time.sleep(1.0)
                    self._verify_chat_open(recipient)
                    return
            except Exception:
                pass


        try:
            results = self.page.get_by_text(
                recipient,
                exact=True,
            )

            count = results.count()

            for index in range(count - 1, -1, -1):
                locator = results.nth(index)

                try:
                    if locator.is_visible(timeout=500):
                        locator.click()
                        time.sleep(1.0)
                        self._verify_chat_open(recipient)
                        return
                except Exception:
                    pass
        except Exception:
            pass


        try:
            search_box.click()
            search_box.press("ArrowDown")
            search_box.press("Enter")
            time.sleep(1.0)
            self._verify_chat_open(recipient)
            return
        except Exception as exc:
            raise RecipientNotFoundError(
                f"Could not open and verify recipient '{recipient}': {exc}"
            ) from exc


    def _clear_stale_file_inputs(self) -> None:
        if self.page is None:
            return

        try:
            self.page.evaluate(
                """
                () => {
                    for (const input of document.querySelectorAll(
                        'input[type="file"]'
                    )) {
                        try {
                            input.value = "";
                        } catch (_) {}
                    }
                }
                """
            )
        except Exception:
            pass

    def _close_native_dialogs(self) -> None:


        for _ in range(3):
            close_persistent_windows_dialogs()
            time.sleep(0.25)


    def _file_input_snapshot(self) -> int:
        if self.page is None:
            return 0

        try:
            return self.page.locator(
                'input[type="file"]'
            ).count()
        except Exception:
            return 0

    def _describe_file_inputs(self) -> None:
        if self.page is None:
            return

        try:
            inputs = self.page.locator(
                'input[type="file"]'
            )

            count = inputs.count()

            logging.info(
                "Current file input count: %d",
                count,
            )

            for index in range(count):
                locator = inputs.nth(index)

                try:
                    accept = (
                        locator.get_attribute("accept")
                        or ""
                    )
                    aria = (
                        locator.get_attribute("aria-label")
                        or ""
                    )
                    title = (
                        locator.get_attribute("title")
                        or ""
                    )

                    logging.info(
                        "File input #%d: accept='%s' aria='%s' title='%s'",
                        index,
                        accept,
                        aria,
                        title,
                    )
                except Exception:
                    pass

        except Exception:
            pass

    def _find_fresh_media_input(self):


        if self.page is None:
            return None

        inputs = self.page.locator(
            'input[type="file"]'
        )

        count = inputs.count()

        if count == 0:
            return None


        for index in range(count - 1, -1, -1):
            locator = inputs.nth(index)

            try:
                accept = (
                    locator.get_attribute("accept")
                    or ""
                ).lower()

                aria = (
                    locator.get_attribute("aria-label")
                    or ""
                ).lower()

                title = (
                    locator.get_attribute("title")
                    or ""
                ).lower()


                if (
                    "video" in accept
                    or "media" in accept
                    or "video" in aria
                    or "video" in title
                    or "media" in aria
                    or "media" in title
                ):
                    return locator
            except Exception:
                pass


        return inputs.nth(count - 1)

    def _open_attachment_menu_and_get_input(self):
        if self.page is None:
            raise VideoSendError(
                "WhatsApp page is not connected."
            )

        before_count = self._file_input_snapshot()

        logging.info(
            "File inputs before attachment action: %d",
            before_count,
        )


        attach_selectors = [
            'button[aria-label*="Attach"]',
            'div[role="button"][aria-label*="Attach"]',
            'button[aria-label*="attachment"]',
            'div[role="button"][aria-label*="attachment"]',
            'span[data-icon="clip"]',
            'span[data-icon="plus"]',
        ]

        clicked = False

        for selector in attach_selectors:
            try:
                locator = self.page.locator(
                    selector
                ).last

                if locator.is_visible(timeout=1000):
                    logging.info(
                        "Opening attachment menu using: %s",
                        selector,
                    )

                    locator.click()
                    clicked = True
                    time.sleep(0.8)
                    break

            except Exception:
                pass


        media_option_selectors = [
            'text="Photos & videos"',
            'text="Photos and videos"',
            'text="Photos & Videos"',
            'text="Photos"',
            'text="Videos"',
        ]

        media_clicked = False

        for selector in media_option_selectors:
            try:
                locator = self.page.locator(
                    selector
                ).last

                if locator.is_visible(timeout=800):
                    logging.info(
                        "Selecting media attachment option: %s",
                        selector,
                    )

                    locator.click()
                    media_clicked = True
                    time.sleep(0.8)
                    break

            except Exception:
                pass

        after_count = self._file_input_snapshot()

        logging.info(
            "File inputs after attachment action: %d",
            after_count,
        )

        self._describe_file_inputs()

        fresh_input = self._find_fresh_media_input()

        if fresh_input is not None:
            logging.info(
                "Fresh media file input found."
            )
            return fresh_input


        if clicked or media_clicked:
            deadline = time.monotonic() + 5

            while time.monotonic() < deadline:
                fresh_input = self._find_fresh_media_input()

                if fresh_input is not None:
                    logging.info(
                        "Fresh media file input appeared."
                    )
                    return fresh_input

                time.sleep(0.25)

        raise VideoSendError(
            "WhatsApp did not expose a fresh media file input "
            "after opening the attachment flow."
        )

    def _attach_video_using_fresh_input(
        self,
        video_path: Path,
    ) -> None:
        if self.page is None:
            raise VideoSendError(
                "WhatsApp page is not connected."
            )

        logging.info(
            "Starting fresh media attachment for: %s",
            video_path.name,
        )


        self._close_native_dialogs()

        file_input = self._open_attachment_menu_and_get_input()

        if file_input is None:
            raise VideoSendError(
                "No fresh media input was available."
            )

        try:


            file_input.set_input_files(
                str(video_path)
            )

            logging.info(
                "MP4 supplied through the fresh WhatsApp media input."
            )

        except Exception as exc:
            self._close_native_dialogs()

            raise VideoSendError(
                f"Fresh media input rejected the video: {exc}"
            ) from exc


        self._close_native_dialogs()


    def _media_preview_visible(self) -> bool:
        if self.page is None:
            return False

        selectors = [
            '[role="dialog"]',
            'video',
            'img[src^="blob:"]',
            'video[src^="blob:"]',
            '[data-testid*="media"]',
            '[aria-label*="Send"]',
        ]

        for selector in selectors:
            try:
                if self.page.locator(selector).first.is_visible(
                    timeout=500
                ):
                    return True
            except Exception:
                pass

        return False

    def _find_send_control(self):
        if self.page is None:
            return None

        selectors = [
            'button[aria-label="Send"]',
            'button[aria-label*="Send"]',
            'div[role="button"][aria-label="Send"]',
            'div[role="button"][aria-label*="Send"]',
            'span[data-icon="send"]',
        ]

        for selector in selectors:
            try:
                locator = self.page.locator(selector).last

                if locator.is_visible(timeout=800):
                    return locator

            except Exception:
                pass

        return None

    def _wait_for_preview(self, seconds: int = 30) -> None:
        logging.info(
            "Waiting for video preview..."
        )

        deadline = time.monotonic() + seconds

        while time.monotonic() < deadline:
            if self._media_preview_visible():
                logging.info(
                    "Media preview detected."
                )
                return

            time.sleep(0.5)

        raise VideoSendError(
            "WhatsApp did not show a media preview."
        )

    def _wait_for_send_completion(
        self,
        seconds: int = 30,
    ) -> None:
        if self.page is None:
            return

        logging.info(
            "Waiting for send operation to complete..."
        )

        deadline = time.monotonic() + seconds


        time.sleep(1.5)

        saw_send_control = True

        while time.monotonic() < deadline:
            send_control = self._find_send_control()

            if send_control is None:
                saw_send_control = False


            if (
                not saw_send_control
                and self._message_composer_visible()
            ):
                logging.info(
                    "Media composer closed and normal message composer returned."
                )
                return


            if not saw_send_control:
                time.sleep(0.8)

                if self._message_composer_visible():
                    logging.info(
                        "Send operation completed; normal composer is available."
                    )
                    return

            time.sleep(0.4)

        raise VideoSendError(
            "Send operation did not return WhatsApp to the normal "
            "message composer within the timeout."
        )


    def send_video(
        self,
        video_path: Path,
        recipient: str,
    ) -> None:
        if self.page is None:
            raise WhatsAppConnectionError(
                "WhatsApp page is not connected."
            )

        video_path = Path(video_path)

        if not video_path.exists():
            raise VideoSendError(
                f"Video file does not exist: {video_path}"
            )

        if video_path.stat().st_size == 0:
            raise VideoSendError(
                f"Video file is empty: {video_path}"
            )

        logging.info(
            "Opening recipient: %s",
            recipient,
        )


        self._close_native_dialogs()
        self._clear_stale_file_inputs()

        self.open_recipient(recipient)


        self._verify_chat_open(recipient)


        self._close_native_dialogs()

        logging.info(
            "Recipient chat verified. Attaching video: %s",
            video_path.name,
        )


        self._attach_video_using_fresh_input(
            video_path
        )

        logging.info(
            "Video supplied directly to the fresh WhatsApp media input."
        )

        self._wait_for_preview()

        logging.info(
            "Looking for Send control..."
        )

        send_control = None
        deadline = time.monotonic() + 15

        while time.monotonic() < deadline:
            send_control = self._find_send_control()

            if send_control is not None:
                break

            time.sleep(0.3)

        if send_control is None:
            self._close_native_dialogs()
            raise VideoSendError(
                "Send control was not found after video attachment."
            )

        logging.info(
            "Send control found."
        )

        try:
            send_control.click()
        except Exception as exc:
            self._close_native_dialogs()

            raise VideoSendError(
                f"Could not click WhatsApp Send control: {exc}"
            ) from exc

        logging.info(
            "Send control clicked."
        )

        try:
            self._wait_for_send_completion()
        finally:


            self._close_native_dialogs()
            self._clear_stale_file_inputs()

        logging.info(
            "Send operation completed."
        )


        time.sleep(1.5)


        self._close_native_dialogs()
        self._clear_stale_file_inputs()

        logging.info(
            "Attachment state reset; ready for the next video."
        )


    def close(self) -> None:
        try:
            self._close_native_dialogs()
        except Exception:
            pass

        try:
            if self.playwright is not None:
                self.playwright.stop()
        except Exception:
            pass

        self.playwright = None
        self.browser = None
        self.page = None
