"""
YLE Teletext reader for the Disobey badge.

Fetches teletext pages from the YLE API and renders them in original
teletext colors on the badge display. Navigate pages with the joystick.

Controls:
  Up/Down    - Cycle through page links (highlighted line)
  Right      - Load the highlighted link
  Left       - Go back to previous page
  B          - Go to next page (nextpg from API)
  A          - Next subpage (if available)
  Select     - Previous subpage (if available)
  Start      - Jump to page 100 (home)
"""

import gc
import time
import uasyncio as asyncio
import network
import requests

from gui.core.ugui import Screen, ssd
from gui.core.writer import CWriter, Writer
from gui.core.colors import (
    BLACK,
    RED,
    GREEN,
    YELLOW,
    BLUE,
    MAGENTA,
    CYAN,
    WHITE,
)
from gui.fonts import font6, tt_mono8
from gui.widgets.label import Label
from bdg.widgets.hidden_active_widget import HiddenActiveWidget
from bdg.asyncbutton import ButtonEvents, ButAct

# ---------------------------------------------------------------------------
# User configuration – edit these values before use
# ---------------------------------------------------------------------------

WIFI_SSID = ""  # WiFi network name
WIFI_PASSWORD = ""  # WiFi password

# YLE API credentials – register at https://developer.yle.fi
APP_ID = ""  # YLE API application ID
APP_KEY = ""  # YLE API application key

HIDE_STATUS = False  # Set True to hide the status bar for more content

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_BASE = "https://external.api.yle.fi"
FETCH_TIMEOUT = 5  # seconds – per-attempt socket timeout
FETCH_RETRIES = 3  # total attempts before giving up

# tt_mono8: monospaced 8x8 – exactly 40 columns across 320 px
CHAR_W = 8
CHAR_H = 8

DISP_W = 320
DISP_H = 170

STATUS_H = 14  # font6 row height used for the status bar
CONTENT_Y = STATUS_H + 1
VISIBLE_LINES = (DISP_H - CONTENT_Y) // CHAR_H  # 19
VISIBLE_COLS = DISP_W // CHAR_W  # 40

TT_LINES = 24  # standard teletext rows
TT_COLS = 40  # standard teletext columns

# Mosaic block dimensions within an 8x8 character cell (2 cols x 3 rows)
BLK_W = 4  # each mosaic column is 4 px wide
BLK_H_TOP = 3  # top row 3 px
BLK_H_MID = 2  # middle row 2 px
BLK_H_BOT = 3  # bottom row 3 px

# Map teletext color names (from the API "structured" content) to badge colors.
TT_COLORS = {
    "black": BLACK,
    "red": RED,
    "green": GREEN,
    "yellow": YELLOW,
    "blue": BLUE,
    "magenta": MAGENTA,
    "cyan": CYAN,
    "white": WHITE,
    # Graphic colours use the same visual values
    "gblack": BLACK,
    "gred": RED,
    "ggreen": GREEN,
    "gyellow": YELLOW,
    "gblue": BLUE,
    "gmagenta": MAGENTA,
    "gcyan": CYAN,
    "gwhite": WHITE,
}


# Characters outside the tt_mono8 ASCII range (32-126) that appear in
# Finnish/Swedish teletext.  Map them to the closest ASCII equivalent so
# that len(text) always equals the number of display columns consumed.
_CHAR_MAP = {
    "ä": "a",
    "ö": "o",
    "å": "a",
    "Ä": "A",
    "Ö": "O",
    "Å": "A",
    "é": "e",
    "É": "E",
    "ü": "u",
    "Ü": "U",
    "ß": "s",
    "ñ": "n",
    "Ñ": "N",
    "à": "a",
    "è": "e",
    "ò": "o",
    "ù": "u",
    "á": "a",
    "í": "i",
    "ó": "o",
    "ú": "u",
    "â": "a",
    "ê": "e",
    "î": "i",
    "ô": "o",
    "û": "u",
    "ç": "c",
    "°": "o",
    "½": " ",
    "¼": " ",
    "£": "L",
    "\u00a0": " ",  # non-breaking space
    "–": "-",  # en-dash
    "—": "-",  # em-dash
    "'": "'",  # right single quote
    "'": "'",  # left single quote
    "\u201c": '"',  # left double quote
    "\u201d": '"',  # right double quote
}


def _sanitize(text):
    """Replace non-renderable characters with ASCII approximations
    and strip embedded newlines that would confuse the Writer."""
    # Remove newlines/carriage-returns – each teletext line is a single row
    text = text.replace("\r", "").replace("\n", "")
    for src, dst in _CHAR_MAP.items():
        if src in text:
            text = text.replace(src, dst)
    return text


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def _fetch_page(page_num, app_id, app_key):
    """Fetch a teletext page as JSON from the YLE API.

    Returns the parsed dict on success, or *None* on any error.
    A socket-level timeout of ``FETCH_TIMEOUT`` seconds is applied so that
    a stalled connection doesn't block the event loop indefinitely.
    """
    url = (
        f"{API_BASE}/v1/teletext/pages/{page_num}.json"
        f"?app_id={app_id}&app_key={app_key}"
    )
    try:
        resp = requests.get(url, timeout=FETCH_TIMEOUT)
        if resp.status_code != 200:
            print(f"Teletext HTTP {resp.status_code}")
            resp.close()
            return None
        data = resp.json()
        resp.close()
        return data
    except Exception as e:
        print(f"Teletext fetch error: {e}")
        return None


# ---------------------------------------------------------------------------
# Page parsing
# ---------------------------------------------------------------------------


def _ensure_list(obj):
    """Wrap a single dict in a list; pass lists through unchanged."""
    if isinstance(obj, dict):
        return [obj]
    return obj if obj else []


def _extract_text(obj):
    """Try common XML-to-JSON text-content keys on *obj*."""
    for key in ("$", "#text", "Text", "text", "_"):
        if key in obj:
            return _sanitize(str(obj[key]))
    return ""


def _parse_page(data):
    """Parse the top-level API response.

    Returns ``(page_num_str, subpage_count, nextpg, subpages)`` where
    *nextpg* is the next page number string (or None), and *subpages*
    is a list of line-lists.  Each line-list has entries (one per
    non-empty teletext row), each of which is a list of
    ``(fg, bg, text)`` tuples.
    """
    try:
        page = data["teletext"]["page"]
        page_num = page.get("number", "???")
        subpage_count = int(page.get("subpagecount", "1"))
        nextpg = page.get("nextpg")
        print(f"[TT] Page {page_num}, subpages: {subpage_count}, nextpg: {nextpg}")

        subpages_raw = _ensure_list(page.get("subpage", []))
        print(f"[TT] Raw subpages count: {len(subpages_raw)}")
        subpages = []
        for sp_idx, sp in enumerate(subpages_raw):
            parsed = _parse_subpage(sp)
            subpages.append(parsed)
            # Debug: print non-empty lines for this subpage
            for li, runs in enumerate(parsed):
                if runs:
                    line_text = "".join(r[2] for r in runs)
                    if line_text.strip():
                        print(f"[TT] Sub{sp_idx} L{li:02d}: {line_text[:60]}")
        return page_num, subpage_count, nextpg, subpages
    except Exception as e:
        print(f"Teletext parse error: {e}")
        return "???", 0, None, []


def _parse_subpage(subpage):
    """Return a compacted list of non-empty line-lists for one subpage.

    Empty lines and lines containing only whitespace are removed so they
    don't waste precious screen real-estate on the small badge display.
    """
    lines = [[] for _ in range(TT_LINES)]

    contents = _ensure_list(subpage.get("content", []))

    # Prefer "structured" (has colour info), fall back to "text"
    structured = None
    text_content = None
    for content in contents:
        ctype = content.get("type", "")
        if ctype == "structured":
            structured = content
            break
        elif ctype == "text":
            text_content = content

    if structured:
        _parse_structured(structured, lines)
    elif text_content:
        _parse_text(text_content, lines)

    # Compact: drop lines that are empty or contain only whitespace.
    # Runs can be 3-tuples (text) or 4-tuples (graphic mosaic).
    compacted = []
    for runs in lines:
        if not runs:
            continue
        text = "".join(r[2] for r in runs)
        if text.strip():
            compacted.append(runs)
    print(f"[TT] Compacted {TT_LINES} -> {len(compacted)} lines")
    return compacted


def _parse_structured(content, lines):
    """Fill *lines* from "structured" content (with per-run colours).

    Text runs are stored as 3-tuples ``(fg, bg, text)``.
    Graphic mosaic runs are stored as 4-tuples ``(fg, bg, text, charcode)``
    where *charcode* is the integer mosaic code for fill_rect rendering.

    Each run's text is normalised to exactly the declared ``length`` so that
    column positions stay correct and lines never exceed 40 columns.
    """
    for line in _ensure_list(content.get("line", [])):
        line_num = int(line.get("number", "1")) - 1
        if not 0 <= line_num < TT_LINES:
            continue
        for run in _ensure_list(line.get("run", [])):
            fg = run.get("fg", "white")
            bg = run.get("bg", "black")
            text = _extract_text(run)
            charcode_str = run.get("charcode")

            # The API ``length`` attribute is authoritative for the column
            # width of the run.  Fall back to len(text) when absent.
            length_str = run.get("length")
            if length_str is not None:
                length = int(length_str)
            else:
                length = len(text) if text else 0
            if length <= 0:
                continue

            # Normalise text to exactly *length* characters so that the
            # rendered line width always matches the teletext 40-column grid.
            if not text:
                text = " " * length
            elif len(text) > length:
                text = text[:length]
            elif len(text) < length:
                text = text + " " * (length - len(text))

            if charcode_str:
                # Graphic mosaic run – parse hex charcode (e.g. "23h" -> 0x23)
                code = int(charcode_str.replace("h", "").replace("H", ""), 16)
                lines[line_num].append((fg, bg, text, code))
            else:
                lines[line_num].append((fg, bg, text))


def _parse_text(content, lines):
    """Fill *lines* from plain "text" content (no colour info)."""
    for line in _ensure_list(content.get("line", [])):
        line_num = int(line.get("number", "1")) - 1
        if not 0 <= line_num < TT_LINES:
            continue
        text = _extract_text(line)
        if text:
            # Truncate to standard teletext line width for safety.
            if len(text) > TT_COLS:
                text = text[:TT_COLS]
            lines[line_num].append(("white", "black", text))


# ---------------------------------------------------------------------------
# Link detection
# ---------------------------------------------------------------------------


def _line_text(lines, idx):
    """Concatenate all run texts for line *idx*.

    Handles both 3-element (text) and 4-element (graphic) run tuples.
    """
    if 0 <= idx < len(lines):
        return "".join(r[2] for r in lines[idx])
    return ""


def _find_links(lines):
    """Return a list of ``(line_idx, col, page_num)`` for every 3-digit
    number in 100..899 found in the page text."""
    links = []
    for li in range(len(lines)):
        text = _line_text(lines, li)
        pos = 0
        tlen = len(text)
        while pos < tlen:
            if text[pos].isdigit():
                start = pos
                while pos < tlen and text[pos].isdigit():
                    pos += 1
                numstr = text[start:pos]
                if len(numstr) == 3:
                    num = int(numstr)
                    if 100 <= num <= 899:
                        links.append((li, start, num))
            else:
                pos += 1
    return links


# ---------------------------------------------------------------------------
# TeletextScreen
# ---------------------------------------------------------------------------


class TeletextScreen(Screen):
    """Main teletext viewer screen."""

    def __init__(self):
        super().__init__()

        # -- config --
        self.hide_status = HIDE_STATUS

        # -- layout (dynamic based on hide_status) --
        if self.hide_status:
            self.content_y = 0
        else:
            self.content_y = CONTENT_Y
        self.visible_lines = (DISP_H - self.content_y) // CHAR_H

        # -- state --
        self.page_num = "100"
        self.subpage_count = 0
        self.nextpg = None  # next page number from API (string or None)
        self.subpages = []  # list of line-lists (one per subpage)
        self.current_sub = 0
        self.scroll_y = 0
        self.links = []  # [(line_idx, col, page_num), ...]
        self.link_idx = -1
        self.history = []  # page-number back-stack
        self.loading = False
        self.connected = False

        # -- network --
        self.sta = network.WLAN(network.STA_IF)

        # -- writers --
        self.wri_status = CWriter(ssd, font6, GREEN, BLACK, verbose=False)
        self.wri_content = CWriter(ssd, tt_mono8, WHITE, BLACK, verbose=False)
        self.wri_content.set_clip(row_clip=True, col_clip=True, wrap=False)

        # -- status label (top bar) --
        self.status_lbl = Label(
            self.wri_status,
            0,
            2,
            DISP_W - 4,
            fgcolor=GREEN,
            bgcolor=BLACK,
            bdcolor=False,
        )
        self.status_lbl.value("YLE Teletext")

        HiddenActiveWidget(self.wri_status)

        # Kick off WiFi + first page load
        self.reg_task(self._init_and_load())

    # -- lifecycle ----------------------------------------------------------

    def after_open(self):
        self.reg_task(self._handle_buttons(), True)

    def on_hide(self):
        """Disconnect WiFi and try to restore ESP-NOW on exit."""
        try:
            self.sta.disconnect()
            self.sta.active(False)
            time.sleep_ms(100)
            self.sta.active(True)
            time.sleep_ms(100)
        except Exception:
            pass

        # Best-effort: reactivate ESP-NOW and restart NowListener
        try:
            espnow_ref = getattr(self, "_espnow_ref", None)
            if espnow_ref:
                espnow_ref.active(True)
            from bdg.msg.connection import NowListener

            NowListener._NowListener__instance = None
            NowListener._NowListener__task = None
            if espnow_ref:
                NowListener.start(espnow_ref)
                print("NowListener restarted")
        except Exception:
            pass

    # -- WiFi / loading -----------------------------------------------------

    async def _init_and_load(self):
        """Connect WiFi and load the initial teletext page."""
        ssid = WIFI_SSID
        password = WIFI_PASSWORD

        if not ssid:
            self.status_lbl.value("No WiFi configured!")
            return

        # Stop NowListener task AND deactivate the ESP-NOW interface
        # so the radio is free for WiFi STA connection.
        self._espnow_ref = None
        try:
            from bdg.msg.connection import NowListener

            NowListener.stop()
            inst = getattr(NowListener, "_NowListener__instance", None)
            if inst is not None:
                self._espnow_ref = getattr(inst, "_NowListener__espnow", None)
                if self._espnow_ref:
                    self._espnow_ref.active(False)
                    print("ESP-NOW deactivated for WiFi")
        except Exception as e:
            print(f"NowListener stop: {e}")

        # Reset STA – force-deactivate to kill any cached auto-reconnect
        self.sta.active(False)
        await asyncio.sleep_ms(300)
        self.sta.active(True)
        await asyncio.sleep_ms(300)

        # If the radio auto-reconnected to a cached SSID, disconnect it
        if self.sta.isconnected():
            cur_cfg = self.sta.config("essid")
            print(f"WiFi auto-connected to '{cur_cfg}', disconnecting...")
            self.sta.disconnect()
            # Wait until actually disconnected
            for _ in range(20):
                if not self.sta.isconnected():
                    break
                await asyncio.sleep_ms(100)
            await asyncio.sleep_ms(200)

        print(f"WiFi: connecting to '{ssid}'")
        self.sta.connect(ssid, password)
        self.status_lbl.value(f"WiFi: {ssid}...")
        await asyncio.sleep_ms(100)

        # Wait for connection (up to ~30 s)
        timeout = 0
        while not self.sta.isconnected() and timeout < 60:
            await asyncio.sleep_ms(500)
            timeout += 1

        status = self.sta.status()
        connected_ssid = self.sta.config("essid") if self.sta.isconnected() else "N/A"
        print(
            f"WiFi status: {status}, connected: {self.sta.isconnected()}, ssid: '{connected_ssid}'"
        )

        if not self.sta.isconnected():
            if status == network.STAT_WRONG_PASSWORD:
                self.status_lbl.value("Wrong WiFi password!")
            elif status == network.STAT_NO_AP_FOUND:
                self.status_lbl.value("WiFi AP not found!")
            else:
                self.status_lbl.value(f"WiFi failed ({status})")
            return

        self.connected = True
        self.status_lbl.value("Connected! Loading p.100")
        await asyncio.sleep_ms(100)
        await self._load_page(100)

    async def _load_page(self, page_num):
        """Fetch, parse, and render a teletext page."""
        if self.loading:
            return
        self.loading = True
        self.status_lbl.value(f"Loading {page_num}...")
        await asyncio.sleep_ms(50)

        gc.collect()

        app_id = APP_ID
        app_key = APP_KEY

        if not app_id or not app_key:
            self.status_lbl.value("No API key! Edit teletext.py")
            self.loading = False
            return

        data = None
        for attempt in range(1, FETCH_RETRIES + 1):
            data = _fetch_page(page_num, app_id, app_key)
            if data is not None:
                break
            if attempt < FETCH_RETRIES:
                self.status_lbl.value(
                    f"Retry {attempt}/{FETCH_RETRIES} p.{page_num}..."
                )
                await asyncio.sleep_ms(500)
                gc.collect()
        if data is None:
            self.status_lbl.value(f"Error page {page_num}")
            self.loading = False
            return

        pnum, scount, nextpg, subpages = _parse_page(data)
        del data  # free JSON memory
        gc.collect()

        self.page_num = pnum
        self.subpage_count = scount
        self.nextpg = nextpg
        self.subpages = subpages
        self.current_sub = 0
        self.scroll_y = 0

        if self.subpages:
            self.links = _find_links(self.subpages[0])
        else:
            self.links = []

        # Auto-select the first link so the highlight is visible immediately
        self.link_idx = 0 if self.links else -1

        print(
            f"[TT] Loaded page {self.page_num}: {len(self.subpages)} subpages, "
            f"{len(self.links)} links, visible_lines={self.visible_lines}, "
            f"VISIBLE_COLS={VISIBLE_COLS}"
        )
        self._render()
        self.loading = False

    # -- rendering ----------------------------------------------------------

    def _cur_lines(self):
        """Lines for the active subpage (already compacted)."""
        if self.subpages and 0 <= self.current_sub < len(self.subpages):
            return self.subpages[self.current_sub]
        return []

    def _render(self):
        """Full redraw of status bar + content area."""
        n_lines = len(self._cur_lines())

        # Status bar text (always compute for the debug log)
        parts = [f"P.{self.page_num}"]
        if self.subpage_count > 1:
            parts.append(f" s{self.current_sub + 1}/{self.subpage_count}")
        if 0 <= self.link_idx < len(self.links):
            parts.append(f" >{self.links[self.link_idx][2]}")
        # Scroll indicator when content exceeds visible area
        if n_lines > self.visible_lines:
            top = self.scroll_y + 1
            bot = min(self.scroll_y + self.visible_lines, n_lines)
            parts.append(f" [{top}-{bot}/{n_lines}]")
        status_text = "".join(parts)
        print(f"[TT] Render: {status_text} scroll_y={self.scroll_y}")

        if not self.hide_status:
            self.status_lbl.value(status_text)

        # Clear content area
        ssd.fill_rect(0, self.content_y, DISP_W, DISP_H - self.content_y, BLACK)

        lines = self._cur_lines()
        n_lines = len(lines)
        for i in range(self.visible_lines):
            li = self.scroll_y + i
            if li >= n_lines:
                break
            self._render_line(lines[li], self.content_y + i * CHAR_H)

        # Highlight the active link line
        self._draw_link_highlight()

        ssd.show()

    def _render_line(self, runs, row_px):
        """Render one teletext line worth of coloured runs.

        Text runs (3-tuples) are rendered with the Writer.
        Graphic mosaic runs (4-tuples) are rendered with fill_rect blocks.

        If the line uses a non-black background but the runs don't fill all
        40 columns, the remainder of the line is filled with that background
        colour so the coloured band extends edge-to-edge.
        """
        Writer.set_textpos(ssd, row_px, 0)
        chars = 0
        line_bg = None  # track last non-black background on this line

        for run in runs:
            if chars >= VISIBLE_COLS:
                break

            # Unpack – 4-element = graphic mosaic, 3-element = text
            if len(run) == 4:
                fg_name, bg_name, text, code = run
            else:
                fg_name, bg_name, text = run
                code = None

            fg = TT_COLORS.get(fg_name, WHITE)
            bg = TT_COLORS.get(bg_name, BLACK)

            # Remember the last non-black background colour
            if bg != BLACK:
                line_bg = bg

            avail = VISIBLE_COLS - chars
            segment = text[:avail]
            n = len(segment)

            if code is not None:
                # Graphic mosaic: render each character cell as a 2x3 block
                for ci in range(n):
                    x = (chars + ci) * CHAR_W
                    self._render_mosaic(code, fg, bg, x, row_px)
                # Advance the Writer cursor to stay in sync (but only if
                # we haven't reached the right edge — set_textpos rejects
                # col >= DISP_W).
                next_col = (chars + n) * CHAR_W
                if next_col < DISP_W:
                    Writer.set_textpos(ssd, row_px, next_col)
            else:
                # Normal text
                self.wri_content.setcolor(fg, bg)
                self.wri_content.printstring(segment)

            chars += n

        # Fill the rest of the line with the line's background colour
        if line_bg is not None and chars < VISIBLE_COLS:
            remaining_x = chars * CHAR_W
            ssd.fill_rect(remaining_x, row_px, DISP_W - remaining_x, CHAR_H, line_bg)

    @staticmethod
    def _render_mosaic(code, fg, bg, x, y):
        """Render one 8x8 teletext mosaic character at pixel (x, y).

        The charcode bits select which of the 6 sub-blocks are filled
        with fg colour (set) or bg colour (clear):
            bit 0 | bit 1
            bit 2 | bit 3
            bit 4 | bit 6
        """
        y_mid = y + BLK_H_TOP
        y_bot = y_mid + BLK_H_MID
        x_r = x + BLK_W
        # Top row
        ssd.fill_rect(x, y, BLK_W, BLK_H_TOP, fg if code & 0x01 else bg)
        ssd.fill_rect(x_r, y, BLK_W, BLK_H_TOP, fg if code & 0x02 else bg)
        # Middle row
        ssd.fill_rect(x, y_mid, BLK_W, BLK_H_MID, fg if code & 0x04 else bg)
        ssd.fill_rect(x_r, y_mid, BLK_W, BLK_H_MID, fg if code & 0x08 else bg)
        # Bottom row
        ssd.fill_rect(x, y_bot, BLK_W, BLK_H_BOT, fg if code & 0x10 else bg)
        ssd.fill_rect(x_r, y_bot, BLK_W, BLK_H_BOT, fg if code & 0x40 else bg)

    def _draw_link_highlight(self):
        """Draw a visible highlight around the active link number.

        Underlines only the 3-digit page number and draws a small ">"
        marker just to its left, so multiple links on one line are
        distinguishable.
        """
        if not 0 <= self.link_idx < len(self.links):
            return
        li, col, _pg = self.links[self.link_idx]
        vis = li - self.scroll_y
        if not 0 <= vis < self.visible_lines:
            return
        y = self.content_y + vis * CHAR_H
        x = col * CHAR_W
        link_w = 3 * CHAR_W  # page numbers are always 3 digits
        # Two-line underline: black border on top for contrast against light
        # backgrounds (green, cyan, yellow), bright white below.
        ssd.hline(x, y + CHAR_H - 2, link_w, BLACK)
        ssd.hline(x, y + CHAR_H - 1, link_w, WHITE)
        # Small ">" marker just left of the number
        if col > 0:
            mx = x - 2
            mid = y + CHAR_H // 2
            for dy in range(-1, 2):
                w = 2 - abs(dy)
                if w > 0:
                    ssd.hline(mx - w + 1, mid + dy, w, WHITE)

    # -- input handling -----------------------------------------------------

    async def _handle_buttons(self):
        """Async loop that reacts to button presses."""
        print("[TT] Button handler started")
        be = ButtonEvents()
        async for button, event in be.get_btn_events():
            print(f"[TT] Button: {button}, event: {event}, loading: {self.loading}")
            if self.loading:
                continue
            if event != ButAct.ACT_PRESS:
                continue

            if button == "btn_u":
                self._cycle_link(-1)
            elif button == "btn_d":
                self._cycle_link(1)
            elif button == "btn_r":
                await self._navigate_link()
            elif button == "btn_l":
                await self._go_back()
            elif button == "btn_b":
                await self._go_next()
            elif button == "btn_a":
                self._cycle_subpage(1)
            elif button == "btn_select":
                self._cycle_subpage(-1)
            elif button == "btn_start":
                await self._go_home()

    # -- navigation helpers -------------------------------------------------

    def _scroll(self, direction):
        """Scroll the viewport by *direction* lines."""
        n_lines = len(self._cur_lines())
        new_y = self.scroll_y + direction
        max_y = max(0, n_lines - self.visible_lines)
        new_y = max(0, min(new_y, max_y))
        print(
            f"[TT] _scroll dir={direction} old={self.scroll_y} new={new_y} "
            f"max={max_y} total={n_lines}"
        )
        if new_y != self.scroll_y:
            self.scroll_y = new_y
            self._render()

    def _cycle_link(self, direction):
        """Move the link highlight forward or backward."""
        if not self.links:
            print("[TT] No links to cycle")
            return
        self.link_idx = (self.link_idx + direction) % len(self.links)
        print(
            f"[TT] Link {self.link_idx}/{len(self.links)}: page {self.links[self.link_idx][2]}"
        )
        # Auto-scroll so the highlighted link is visible
        li = self.links[self.link_idx][0]
        if li < self.scroll_y:
            self.scroll_y = li
        elif li >= self.scroll_y + self.visible_lines:
            self.scroll_y = li - self.visible_lines + 1
        self._render()

    async def _navigate_link(self):
        """Jump to the page number of the currently highlighted link."""
        if not 0 <= self.link_idx < len(self.links):
            return
        _, _, target = self.links[self.link_idx]
        self._push_history()
        await self._load_page(target)

    async def _go_back(self):
        """Pop the history stack and load the previous page."""
        if self.history:
            prev = self.history.pop()
            await self._load_page(prev)

    async def _go_next(self):
        """Navigate to the next teletext page (from API 'nextpg')."""
        if self.connected and self.nextpg:
            print(f"[TT] Next page: {self.nextpg}")
            self._push_history()
            await self._load_page(int(self.nextpg))

    async def _go_home(self):
        """Navigate to page 100 (teletext home)."""
        if self.connected:
            self._push_history()
            await self._load_page(100)

    def _cycle_subpage(self, direction=1):
        """Cycle to the next/previous subpage of the current page."""
        if self.subpage_count <= 1:
            return
        self.current_sub = (self.current_sub + direction) % self.subpage_count
        self.scroll_y = 0
        self.links = _find_links(self._cur_lines())
        self.link_idx = 0 if self.links else -1
        self._render()

    def _push_history(self):
        """Record the current page number on the back-stack."""
        try:
            self.history.append(int(self.page_num))
        except ValueError:
            pass
        if len(self.history) > 10:
            self.history = self.history[-10:]


# ---------------------------------------------------------------------------
# Game registry entry
# ---------------------------------------------------------------------------


def badge_game_config():
    return {
        "con_id": 21,
        "title": "YLE Teksti-tv",
        "screen_class": TeletextScreen,
        "screen_args": (),
        "multiplayer": False,
        "description": "Browse YLE Teletext pages",
    }
