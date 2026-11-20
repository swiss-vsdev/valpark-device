"""Rendu e-paper : 22 caractères par ligne, redessin seulement si version change."""
from __future__ import annotations

import importlib
import sys

from .config import Config

ICON_GLYPH = {
    "idle": " ",
    "paid": "$",
    "timer": "T",
    "warning": "!",
    "error": "X",
}


class Display:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.last_version: str | None = None
        self.epd = None
        if not cfg.mock:
            sys.path.insert(0, str(cfg.vendor_dir))
            module = importlib.import_module(f"waveshare_epd.{cfg.epd_model}")
            self.epd = module.EPD()
            self.epd.init(self.epd.FULL_UPDATE)
            self.epd.Clear()

    def render(self, display: dict) -> None:
        version = display.get("version")
        if version is None or version == self.last_version:
            return
        self.last_version = version

        lines = [str(display.get(key, ""))[:22] for key in ("line1", "line2", "line3")]
        icon = ICON_GLYPH.get(display.get("icon", "idle"), " ")
        if self.cfg.mock:
            frame = "█" if display.get("inverted") else "│"
            print(f"  ┌──────────────────────┐ {icon} v={version}")
            for line in lines:
                print(f"  {frame} {line:<22} {frame}")
            print("  └──────────────────────┘")
            return

        from PIL import Image, ImageDraw, ImageFont

        image = Image.new("1", (self.epd.width, self.epd.height), 1)
        draw = ImageDraw.Draw(image)
        inverted = bool(display.get("inverted"))
        background, foreground = (0, 255) if inverted else (255, 0)
        draw.rectangle((0, 0, image.width, image.height), fill=background)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except OSError:
            font = ImageFont.load_default()

        for index, line in enumerate(lines):
            draw.text((4, index * 38 + 4), line, font=font, fill=foreground)
        if icon != " ":
            draw.text((image.width - 20, 2), icon, font=font, fill=foreground)

        buffer_fn = getattr(self.epd, "getbuffer", None) or self.epd.get_frame_buffer
        self.epd.display(buffer_fn(image))
        self.epd.sleep()


def apply_state(display: Display, state: dict) -> None:
    """Applique la réponse /events ou /state (display + pollSeconds)."""
    if "display" in state:
        display.render(state["display"])
