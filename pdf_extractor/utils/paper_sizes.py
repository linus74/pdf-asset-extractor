"""
Paper sizes definition and identification utility.
Converts PDF points to mm/inches and matches standard international formats.
"""

from typing import Tuple, Optional, Dict

# Points to mm conversion factor (72 points per inch, 25.4 mm per inch)
PT_TO_MM = 25.4 / 72.0
MM_TO_PT = 72.0 / 25.4
PT_TO_INCH = 1.0 / 72.0

# Standard paper sizes in points (width x height in portrait)
KNOWN_PAPER_SIZES: Dict[str, Tuple[float, float]] = {
    # ISO A Series
    "A0": (2383.94, 3370.39),
    "A1": (1683.78, 2383.94),
    "A2": (1190.55, 1683.78),
    "A3": (841.89, 1190.55),
    "A4": (595.28, 841.89),
    "A5": (419.53, 595.28),
    "A6": (297.64, 419.53),
    "A7": (209.76, 297.64),
    "A8": (147.40, 209.76),
    # ISO B Series
    "B0": (2834.65, 4008.19),
    "B1": (2004.09, 2834.65),
    "B2": (1417.32, 2004.09),
    "B3": (1000.63, 1417.32),
    "B4": (708.66, 1000.63),
    "B5": (498.90, 708.66),
    "B6": (354.33, 498.90),
    # North American
    "Letter": (612.0, 792.0),
    "Legal": (612.0, 1008.0),
    "Tabloid / Ledger": (792.0, 1224.0),
    "Junior Legal": (360.0, 576.0),
    "Executive": (522.0, 756.0),
    "Half Letter": (396.0, 612.0),
    # Commercial / Card sizes
    "Business Card (EU 85x55mm)": (155.91, 240.94),
    "Business Card (US 3.5x2in)": (144.0, 252.0),
    "Postcard (105x148mm)": (297.64, 419.53),
    "Envelope DL (110x220mm)": (311.81, 623.62),
    "Envelope C5 (162x229mm)": (459.21, 649.13),
}


def points_to_mm(pt: float) -> float:
    return round(pt * PT_TO_MM, 2)


def points_to_inches(pt: float) -> float:
    return round(pt * PT_TO_INCH, 2)


def identify_paper_size(width_pt: float, height_pt: float, tolerance_pt: float = 3.5) -> Tuple[str, str]:
    """
    Identifies standard paper size and orientation.
    Returns: (size_name, orientation) e.g. ("A4", "Portrait")
    """
    w = abs(width_pt)
    h = abs(height_pt)

    if abs(w - h) < tolerance_pt:
        orientation = "Square"
    elif w > h:
        orientation = "Landscape"
        # normalize to portrait for matching
        w, h = h, w
    else:
        orientation = "Portrait"

    for name, (std_w, std_h) in KNOWN_PAPER_SIZES.items():
        if abs(w - std_w) <= tolerance_pt and abs(h - std_h) <= tolerance_pt:
            return name, orientation

    # If no standard size matched, return custom formatted size in mm
    w_mm = points_to_mm(w)
    h_mm = points_to_mm(h)
    return f"Custom ({w_mm} × {h_mm} mm)", orientation
