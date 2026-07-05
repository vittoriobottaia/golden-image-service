"""Golden branded card renderer (server-side, Pillow).

Renders a 1080x1080 Instagram/ads carousel card from a base photo + text,
applying the Golden brand system (palette, legibility gradient, hairline
expedition frame, GOLDEN wordmark, kicker + Playfair headline).

Designed to replace the Browserless HTML screenshot render used by the
carousel n8n workflow: one deterministic HTTP call, no headless browser.
"""

import io
import os
import time
from typing import Optional, List, Tuple

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, UnidentifiedImageError


class CardError(Exception):
    """Raised when a card cannot be rendered."""


# ---- Golden brand palette (RGB) ----
PARANA_GREEN = (71, 74, 55)      # #474A37
GOLDEN_OLIVE = (153, 153, 102)   # #999966
CREAM = (245, 243, 239)          # #F5F3EF
DORADO_GOLD = (211, 82, 42)      # #D3522A
INK = (51, 53, 42)               # #33352a

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")


class CardService:
    MAX_FETCH_BYTES = 25 * 1024 * 1024
    FETCH_TIMEOUT_S = 30
    FETCH_RETRIES = 3
    # Overlay strength -> bottom-gradient max alpha (0-255)
    STRENGTH_ALPHA = {"light": 175, "medium": 217, "strong": 242}
    # Design variant presets (from DESIGN_VARIATION_SELECTOR agent)
    VARIANT_PRESETS = {
        "editorial_dark":  {"strength": "strong"},
        "cinematic_hero":  {"strength": "medium"},
        "technical_guide": {"strength": "medium"},
        "lodge_warm":      {"strength": "medium"},
        "premium_minimal": {"strength": "light"},
        "story_proof":     {"strength": "medium"},
        "cta_clean":       {"strength": "strong", "center": True},
    }
    RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}
    FETCH_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://goldenflyfishing.com/",
    }

    def __init__(self) -> None:
        self.service_name = "Golden Media API"

    # ---------- public entrypoint ----------
    def render_card(
        self,
        image_url: str,
        kicker: str = "",
        headline: str = "",
        sub_text: str = "",
        wordmark: str = "GOLDEN",
        location: str = "",
        role: str = "",
        mode: str = "auto",
        accent: bool = True,
        size: int = 1080,
        quality: int = 92,
        design_variant: str = "",
        overlay_strength: str = "",
        typography_style: str = "",
    ) -> io.BytesIO:
        if not image_url:
            raise CardError("image_url is required")

        base_photo = self._fetch_image(image_url)

        # Resolve design variant -> overlay strength, layout, headline font
        preset = self.VARIANT_PRESETS.get(str(design_variant).lower(), {})
        strength = (str(overlay_strength).lower() or preset.get("strength", "medium"))
        grad_alpha = self.STRENGTH_ALPHA.get(strength, 217)
        is_cta = str(role).lower() in {"cta", "cta_cover", "conversion"} or preset.get("center", False)
        head_font = ("Inter-SemiBold.ttf"
                     if str(typography_style).lower() in {"modern_sans", "sans"}
                     else "PlayfairDisplay-SemiBold.ttf")

        # Decide crop strategy
        chosen = mode
        if mode == "auto":
            w, h = base_photo.size
            # Wide/panoramic or very tall photos look bad cropped square -> contain
            chosen = "contain" if (w > h * 1.15 or h > w * 1.30) else "cover"

        if chosen == "contain":
            canvas = self._contain_with_blur(base_photo, size, size)
        else:
            canvas = self._cover(base_photo, size, size)

        # Legibility + brand layers (gradient intensity driven by overlay strength)
        canvas = self._apply_bottom_gradient(canvas, max_alpha=grad_alpha,
                                             start=(0.28 if is_cta else 0.42))
        if is_cta:
            canvas = self._apply_flat_veil(canvas, alpha=(110 if strength == "strong" else 80))
        canvas = self._apply_frame(canvas)

        draw = ImageDraw.Draw(canvas)
        self._draw_wordmark(draw, wordmark, size)
        if location:
            self._draw_location(draw, location, size)

        if is_cta:
            self._draw_center_block(canvas, draw, kicker, headline, sub_text, accent, size,
                                    head_font, show_pill=(str(role).lower() == "cta_cover"))
        else:
            self._draw_bottom_left_block(draw, kicker, headline, accent, size, head_font)

        out = io.BytesIO()
        canvas.convert("RGB").save(out, format="JPEG", quality=quality, optimize=True)
        out.seek(0)
        return out

    # ---------- image acquisition ----------
    def _fetch_image(self, url: str) -> Image.Image:
        last_error = "unknown error"
        for attempt in range(self.FETCH_RETRIES):
            try:
                resp = requests.get(
                    url,
                    timeout=self.FETCH_TIMEOUT_S,
                    headers=self.FETCH_HEADERS,
                    stream=True,
                )
            except requests.RequestException as exc:
                last_error = str(exc)
            else:
                if resp.status_code in self.RETRY_STATUS:
                    last_error = f"{resp.status_code} Server Error for url: {url}"
                elif not resp.ok:
                    raise CardError(f"Could not fetch image_url: {resp.status_code} for url: {url}")
                else:
                    data = resp.content
                    if not data:
                        raise CardError("Fetched image is empty")
                    if len(data) > self.MAX_FETCH_BYTES:
                        raise CardError("Fetched image exceeds the 25 MB limit")
                    try:
                        image = Image.open(io.BytesIO(data))
                        image = ImageOps.exif_transpose(image)
                        image.load()
                    except (UnidentifiedImageError, OSError, ValueError) as exc:
                        raise CardError("Fetched file is not a valid image") from exc
                    return self._ensure_rgb(image)

            if attempt < self.FETCH_RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))

        raise CardError(f"Could not fetch image_url after {self.FETCH_RETRIES} attempts: {last_error}")

    def _ensure_rgb(self, image: Image.Image) -> Image.Image:
        if image.mode in {"RGBA", "LA", "P"}:
            rgba = image.convert("RGBA")
            bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            bg.alpha_composite(rgba)
            return bg.convert("RGB")
        if image.mode != "RGB":
            return image.convert("RGB")
        return image

    # ---------- crop strategies ----------
    def _cover(self, image: Image.Image, w: int, h: int) -> Image.Image:
        sw, sh = image.size
        scale = max(w / sw, h / sh)
        nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
        resized = image.resize((nw, nh), Image.LANCZOS)
        left = (nw - w) // 2
        top = (nh - h) // 2
        return resized.crop((left, top, left + w, top + h))

    def _contain_with_blur(self, image: Image.Image, w: int, h: int) -> Image.Image:
        # Blurred full-canvas background from the same image
        background = self._cover(image, w, h).filter(ImageFilter.GaussianBlur(radius=26))
        canvas = Image.new("RGB", (w, h), INK)
        canvas.paste(background, (0, 0))
        # Ink veil over the blur so the contained photo pops
        veil = Image.new("RGBA", (w, h), INK + (100,))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), veil).convert("RGB")
        # Contained photo, centered
        sw, sh = image.size
        scale = min(w / sw, h / sh)
        nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
        main = image.resize((nw, nh), Image.LANCZOS)
        canvas.paste(main, ((w - nw) // 2, (h - nh) // 2))
        return canvas

    # ---------- brand overlays ----------
    def _apply_bottom_gradient(self, canvas: Image.Image, max_alpha: int = 217,
                               start: float = 0.42) -> Image.Image:
        w, h = canvas.size
        grad = Image.new("L", (1, h), 0)
        for y in range(h):
            frac = y / (h - 1)
            if frac < start:
                a = 0
            else:
                a = int(max_alpha * ((frac - start) / (1 - start)))
            grad.putpixel((0, y), a)
        grad = grad.resize((w, h))
        overlay = Image.new("RGB", (w, h), INK)
        result = canvas.convert("RGB").copy()
        result.paste(overlay, (0, 0), grad)
        return result

    def _apply_flat_veil(self, canvas: Image.Image, alpha: int = 90) -> Image.Image:
        w, h = canvas.size
        veil = Image.new("RGBA", (w, h), INK + (alpha,))
        return Image.alpha_composite(canvas.convert("RGBA"), veil).convert("RGB")

    def _apply_frame(self, canvas: Image.Image) -> Image.Image:
        w, h = canvas.size
        inset = 34
        frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        fd = ImageDraw.Draw(frame)
        fd.rectangle([inset, inset, w - inset - 1, h - inset - 1],
                     outline=GOLDEN_OLIVE + (90,), width=1)
        return Image.alpha_composite(canvas.convert("RGBA"), frame).convert("RGB")

    # ---------- text ----------
    def _font(self, filename: str, size: int) -> ImageFont.FreeTypeFont:
        path = os.path.join(FONTS_DIR, filename)
        try:
            font = ImageFont.truetype(path, size)
        except (OSError, IOError):
            try:
                return ImageFont.load_default(size)
            except TypeError:
                return ImageFont.load_default()
        # Playfair Display ships as a variable font that defaults to Regular;
        # pin the weight axis to SemiBold (600) so headlines render on-brand.
        if "playfair" in filename.lower():
            try:
                font.set_variation_by_axes([600])
            except (AttributeError, OSError, ValueError):
                pass
        return font

    def _text_width(self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
                    tracking: int = 0) -> int:
        if tracking <= 0:
            return int(draw.textlength(text, font=font))
        total = 0
        for ch in text:
            total += int(draw.textlength(ch, font=font)) + tracking
        return max(0, total - tracking)

    def _draw_tracked(self, draw: ImageDraw.ImageDraw, xy: Tuple[int, int], text: str,
                      font: ImageFont.FreeTypeFont, fill, tracking: int = 0) -> None:
        x, y = xy
        if tracking <= 0:
            draw.text((x, y), text, font=font, fill=fill)
            return
        for ch in text:
            draw.text((x, y), ch, font=font, fill=fill)
            x += int(draw.textlength(ch, font=font)) + tracking

    def _wrap(self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
              max_width: int) -> List[str]:
        words = (text or "").split()
        lines: List[str] = []
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if draw.textlength(candidate, font=font) <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    def _draw_wordmark(self, draw: ImageDraw.ImageDraw, wordmark: str, size: int) -> None:
        font = self._font("Inter-SemiBold.ttf", 26)
        self._draw_tracked(draw, (64, 52), (wordmark or "GOLDEN").upper(), font, CREAM, tracking=6)

    def _draw_location(self, draw: ImageDraw.ImageDraw, location: str, size: int) -> None:
        font = self._font("Inter-Regular.ttf", 22)
        text = location.upper()
        width = self._text_width(draw, text, font, tracking=2)
        self._draw_tracked(draw, (size - 64 - width, 56), text, font, GOLDEN_OLIVE, tracking=2)

    def _draw_bottom_left_block(self, draw: ImageDraw.ImageDraw, kicker: str, headline: str,
                                accent: bool, size: int,
                                head_font: str = "PlayfairDisplay-SemiBold.ttf") -> None:
        margin = 64
        max_width = size - margin * 2
        kfont = self._font("Inter-SemiBold.ttf", 24)
        hfont = self._font(head_font, 60)
        lines = self._wrap(draw, headline, hfont, max_width)
        line_h = int(hfont.size * 1.06)

        headline_h = line_h * len(lines)
        kicker_h = kfont.size + 14 if kicker else 0
        rule_h = 2 + 16 if accent else 0
        block_h = rule_h + kicker_h + headline_h
        y = size - 84 - block_h

        if accent:
            draw.rectangle([margin, y, margin + 64, y + 2], fill=DORADO_GOLD)
            y += 2 + 16
        if kicker:
            self._draw_tracked(draw, (margin, y), kicker.upper(), kfont, GOLDEN_OLIVE, tracking=3)
            y += kfont.size + 14
        for line in lines:
            draw.text((margin, y), line, font=hfont, fill=CREAM)
            y += line_h

    def _draw_center_block(self, canvas: Image.Image, draw: ImageDraw.ImageDraw, kicker: str,
                           headline: str, sub_text: str, accent: bool, size: int,
                           head_font: str = "PlayfairDisplay-SemiBold.ttf",
                           show_pill: bool = False) -> None:
        margin = 90
        max_width = size - margin * 2
        kfont = self._font("Inter-SemiBold.ttf", 24)
        hfont = self._font(head_font, 66)
        sfont = self._font("Inter-Regular.ttf", 28)

        lines = self._wrap(draw, headline, hfont, max_width)
        line_h = int(hfont.size * 1.06)
        sub_lines = self._wrap(draw, sub_text, sfont, max_width) if sub_text else []
        sub_line_h = int(sfont.size * 1.25)

        pill_h = 46 + 24 if show_pill else 0
        rule_h = 2 + 18 if accent else 0
        kicker_h = kfont.size + 16 if kicker else 0
        headline_h = line_h * len(lines)
        sub_h = sub_line_h * len(sub_lines)
        block_h = pill_h + rule_h + kicker_h + headline_h + (24 + sub_h if sub_lines else 0)
        y = (size - block_h) // 2

        def center_x(width: int) -> int:
            return (size - width) // 2

        if show_pill:
            self._draw_pill(draw, "FREE GUIDE · PDF", size, y)
            y += pill_h
        if accent:
            draw.rectangle([center_x(64), y, center_x(64) + 64, y + 2], fill=DORADO_GOLD)
            y += 2 + 18
        if kicker:
            kw = self._text_width(draw, kicker.upper(), kfont, tracking=3)
            self._draw_tracked(draw, (center_x(kw), y), kicker.upper(), kfont, GOLDEN_OLIVE, tracking=3)
            y += kfont.size + 16
        for line in lines:
            lw = int(draw.textlength(line, font=hfont))
            draw.text((center_x(lw), y), line, font=hfont, fill=CREAM)
            y += line_h
        if sub_lines:
            y += 24
            for line in sub_lines:
                lw = int(draw.textlength(line, font=sfont))
                draw.text((center_x(lw), y), line, font=sfont, fill=CREAM)
                y += sub_line_h

    def _draw_pill(self, draw: ImageDraw.ImageDraw, text: str, size: int, y: int) -> None:
        font = self._font("Inter-SemiBold.ttf", 20)
        tw = self._text_width(draw, text, font, tracking=2)
        pad_x, pad_y = 26, 12
        pill_w = tw + pad_x * 2
        pill_h = font.size + pad_y * 2
        x0 = (size - pill_w) // 2
        draw.rounded_rectangle([x0, y, x0 + pill_w, y + pill_h], radius=pill_h // 2,
                               outline=DORADO_GOLD, width=2)
        self._draw_tracked(draw, (x0 + pad_x, y + pad_y - 1), text, font, CREAM, tracking=2)
