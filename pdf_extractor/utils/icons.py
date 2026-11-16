"""
Crisp high-DPI minimal icons & application .ico generator using Pillow supersampling.
Avoids blurry or inconsistent system emojis in Desktop GUI widgets.
"""

from pathlib import Path
from typing import Dict
from PIL import Image, ImageDraw
import customtkinter as ctk


def _render_icon(name: str, color: str, size: int = 20) -> Image.Image:
    """
    Draws a clean geometric icon at 3x resolution and downsamples with LANCZOS for crisp anti-aliasing.
    """
    s = size * 3
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lw = max(3, int(s * 0.08))  # stroke width
    pad = int(s * 0.14)

    if name == "upload":
        # Tray + Up arrow
        draw.line([(pad, s - pad), (s - pad, s - pad)], fill=color, width=lw)
        draw.line([(pad, s - pad), (pad, int(s * 0.65))], fill=color, width=lw)
        draw.line([(s - pad, s - pad), (s - pad, int(s * 0.65))], fill=color, width=lw)
        cx = s // 2
        draw.line([(cx, int(s * 0.68)), (cx, pad)], fill=color, width=lw)
        draw.line([(cx, pad), (int(s * 0.30), int(s * 0.36))], fill=color, width=lw)
        draw.line([(cx, pad), (int(s * 0.70), int(s * 0.36))], fill=color, width=lw)

    elif name == "image":
        # Rounded frame + mountain + sun
        draw.rounded_rectangle([pad, pad, s - pad, s - pad], radius=int(s * 0.12), outline=color, width=lw)
        r_sun = int(s * 0.08)
        sx, sy = int(s * 0.34), int(s * 0.36)
        draw.ellipse([sx - r_sun, sy - r_sun, sx + r_sun, sy + r_sun], fill=color)
        draw.line(
            [(pad + lw, s - pad - lw), (int(s * 0.45), int(s * 0.56)), (int(s * 0.62), int(s * 0.70)), (int(s * 0.75), int(s * 0.50)), (s - pad - lw, s - pad - lw)],
            fill=color, width=lw, joint="curve"
        )

    elif name == "vector":
        # Bezier nodes + curve
        node_r = int(s * 0.09)
        p1 = (pad + node_r, s - pad - node_r)
        p2 = (s - pad - node_r, pad + node_r)
        draw.line([p1, p2], fill=color, width=lw)
        draw.rectangle([p1[0] - node_r, p1[1] - node_r, p1[0] + node_r, p1[1] + node_r], fill=color)
        draw.rectangle([p2[0] - node_r, p2[1] - node_r, p2[0] + node_r, p2[1] + node_r], fill=color)
        # Control handles
        c1 = (pad + node_r, pad + node_r)
        c2 = (s - pad - node_r, s - pad - node_r)
        draw.line([p1, c1], fill=color, width=max(2, lw // 2))
        draw.ellipse([c1[0] - node_r // 2, c1[1] - node_r // 2, c1[0] + node_r // 2, c1[1] + node_r // 2], outline=color, width=max(2, lw // 2))
        draw.line([p2, c2], fill=color, width=max(2, lw // 2))
        draw.ellipse([c2[0] - node_r // 2, c2[1] - node_r // 2, c2[0] + node_r // 2, c2[1] + node_r // 2], outline=color, width=max(2, lw // 2))

    elif name == "font":
        # Stylized geometric "A"
        cx = s // 2
        draw.line([(cx, pad), (pad + int(s * 0.06), s - pad)], fill=color, width=lw)
        draw.line([(cx, pad), (s - pad - int(s * 0.06), s - pad)], fill=color, width=lw)
        draw.line([(int(s * 0.30), int(s * 0.64)), (int(s * 0.70), int(s * 0.64))], fill=color, width=lw)

    elif name == "palette":
        # Overlapping color circles (RGB / CMYK feel)
        r = int(s * 0.24)
        draw.ellipse([s // 2 - r, pad, s // 2 + r, pad + 2 * r], outline=color, width=lw)
        draw.ellipse([pad, s - pad - 2 * r, pad + 2 * r, s - pad], outline=color, width=lw)
        draw.ellipse([s - pad - 2 * r, s - pad - 2 * r, s - pad, s - pad], outline=color, width=lw)

    elif name == "attachment":
        # Paperclip
        draw.arc([int(s * 0.26), pad, int(s * 0.74), int(s * 0.52)], start=180, end=0, fill=color, width=lw)
        draw.line([(int(s * 0.26), int(s * 0.30)), (int(s * 0.26), int(s * 0.74))], fill=color, width=lw)
        draw.line([(int(s * 0.74), int(s * 0.30)), (int(s * 0.74), int(s * 0.70))], fill=color, width=lw)
        draw.arc([int(s * 0.35), int(s * 0.56), int(s * 0.74), s - pad], start=0, end=180, fill=color, width=lw)
        draw.line([(int(s * 0.35), int(s * 0.74)), (int(s * 0.35), int(s * 0.40))], fill=color, width=lw)

    elif name == "folder":
        # Clean folder outline
        draw.polygon(
            [
                (pad, pad + int(s * 0.12)),
                (int(s * 0.42), pad + int(s * 0.12)),
                (int(s * 0.52), pad + int(s * 0.24)),
                (s - pad, pad + int(s * 0.24)),
                (s - pad, s - pad),
                (pad, s - pad),
            ],
            outline=color,
            width=lw,
        )

    elif name == "globe":
        # Web / HTML report icon
        draw.ellipse([pad, pad, s - pad, s - pad], outline=color, width=lw)
        draw.ellipse([int(s * 0.34), pad, int(s * 0.66), s - pad], outline=color, width=max(2, lw - 1))
        draw.line([(pad, s // 2), (s - pad, s // 2)], fill=color, width=max(2, lw - 1))

    elif name == "sun":
        cx, cy = s // 2, s // 2
        r = int(s * 0.18)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=lw)
        # Rays
        import math
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = cx + int(math.cos(rad) * (r + lw * 1.4))
            y1 = cy + int(math.sin(rad) * (r + lw * 1.4))
            x2 = cx + int(math.cos(rad) * (s * 0.42))
            y2 = cy + int(math.sin(rad) * (s * 0.42))
            draw.line([(x1, y1), (x2, y2)], fill=color, width=lw)

    elif name == "moon":
        draw.ellipse([pad, pad, s - pad, s - pad], fill=color)
        # Carve out inner circle for crescent
        draw.ellipse([int(s * 0.36), int(s * 0.10), int(s * 1.02), int(s * 0.76)], fill=(0, 0, 0, 0))

    elif name == "lock":
        # Padlock
        draw.arc([int(s * 0.30), pad, int(s * 0.70), int(s * 0.58)], start=180, end=0, fill=color, width=lw)
        draw.rounded_rectangle([int(s * 0.22), int(s * 0.44), int(s * 0.78), s - pad], radius=int(s * 0.08), outline=color, width=lw)

    elif name == "files":
        # Stacked documents for batch queue
        off = int(s * 0.14)
        draw.rounded_rectangle([pad + off, pad, s - pad, s - pad - off], radius=int(s * 0.08), outline=color, width=max(2, lw - 1))
        draw.rounded_rectangle([pad, pad + off, s - pad - off, s - pad], radius=int(s * 0.08), fill=None, outline=color, width=lw)

    elif name == "plus":
        cx, cy = s // 2, s // 2
        draw.line([(cx, pad + int(s * 0.06)), (cx, s - pad - int(s * 0.06))], fill=color, width=lw)
        draw.line([(pad + int(s * 0.06), cy), (s - pad - int(s * 0.06), cy)], fill=color, width=lw)

    elif name == "logo":
        # App emblem: sleek geometric document + prism layer
        draw.rounded_rectangle([pad, pad, s - pad, s - pad], radius=int(s * 0.18), fill="#0284c7")
        # Inner folded sheet lines
        p_l = int(s * 0.30)
        p_r = int(s * 0.70)
        draw.line([(p_l, int(s * 0.38)), (p_r, int(s * 0.38))], fill="#ffffff", width=lw)
        draw.line([(p_l, int(s * 0.52)), (int(s * 0.60), int(s * 0.52))], fill="#bae6fd", width=lw)
        draw.line([(p_l, int(s * 0.66)), (int(s * 0.50), int(s * 0.66))], fill="#7dd3fc", width=lw)

    return img.resize((size, size), Image.Resampling.LANCZOS)


def get_ctk_icon(name: str, size: int = 18, light_color: str = "#334155", dark_color: str = "#94a3b8") -> ctk.CTkImage:
    """Returns an adaptive CTkImage supporting both Light and Dark themes."""
    if name == "logo":
        light_img = _render_icon("logo", "#ffffff", size=size)
        dark_img = _render_icon("logo", "#ffffff", size=size)
        return ctk.CTkImage(light_image=light_img, dark_image=dark_img, size=(size, size))

    light_img = _render_icon(name, light_color, size=size)
    dark_img = _render_icon(name, dark_color, size=size)
    return ctk.CTkImage(light_image=light_img, dark_image=dark_img, size=(size, size))


def create_app_ico(output_path: str | Path) -> Path:
    """
    Generates a crisp multi-resolution Windows .ico file for the compiled executable.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded square squircle base (deep slate gradient simulation)
    draw.rounded_rectangle([12, 12, 244, 244], radius=56, fill="#0f172a", outline="#38bdf8", width=8)

    # Stylized PDF Document card inside
    draw.rounded_rectangle([54, 42, 174, 198], radius=16, fill="#1e293b", outline="#64748b", width=5)

    # Vector prism / layers popping out on the right
    draw.rounded_rectangle([122, 88, 206, 172], radius=14, fill="#0284c7", outline="#bae6fd", width=5)
    # Bezier curve / node accent inside layer
    draw.line([(142, 148), (186, 110)], fill="#ffffff", width=6)
    draw.ellipse([134, 140, 150, 156], fill="#38bdf8", outline="#ffffff", width=3)
    draw.ellipse([178, 102, 194, 118], fill="#38bdf8", outline="#ffffff", width=3)

    # Typography lines on document
    draw.line([(76, 74), (146, 74)], fill="#f8fafc", width=8)
    draw.line([(76, 102), (112, 102)], fill="#94a3b8", width=6)
    draw.line([(76, 126), (112, 126)], fill="#94a3b8", width=6)

    # Save multi-size ICO
    img.save(str(out), format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return out
