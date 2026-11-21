"""
Color profile and spot color extractor: extracts embedded ICC profiles,
parses ICC headers with Pillow/ImageCms, and identifies spot colorants/separations.
"""

import io
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import pikepdf
from PIL import ImageCms
from ..utils.helpers import sanitize_filename, format_bytes, compute_sha256

# ICC Profile Device Classes
DEVICE_CLASSES = {
    b"scnr": "Input Device (Scanner/Camera)",
    b"mntr": "Display Device (Monitor)",
    b"prtr": "Output Device (Printer/Press)",
    b"link": "DeviceLink Profile",
    b"spac": "ColorSpace Conversion Profile",
    b"abst": "Abstract Profile",
    b"nmcl": "Named Color Profile",
}

# Standard process inks to ignore when searching for spot colors
STANDARD_PROCESS_INKS = {"cyan", "magenta", "yellow", "black", "all", "none"}


def _parse_icc_header(data: bytes) -> Dict[str, Any]:
    header = {
        "description": "Unknown Profile",
        "device_class": "Unknown",
        "color_space": "Unknown",
        "connection_space": "Unknown",
        "version": "Unknown",
    }
    if len(data) < 128:
        return header

    # ICC version at byte 8
    major = data[8]
    minor = (data[9] >> 4) & 0x0F
    bugfix = data[9] & 0x0F
    header["version"] = f"{major}.{minor}.{bugfix}"

    # Device class (bytes 12-16)
    dev_class = data[12:16]
    header["device_class"] = DEVICE_CLASSES.get(dev_class, dev_class.decode("ascii", errors="ignore").strip())

    # Data color space (bytes 16-20)
    cs = data[16:20].decode("ascii", errors="ignore").strip()
    header["color_space"] = cs

    # Profile connection space (bytes 20-24)
    pcs = data[20:24].decode("ascii", errors="ignore").strip()
    header["connection_space"] = pcs

    # Human-readable profile description via Pillow ImageCms
    try:
        desc = ImageCms.getProfileDescription(io.BytesIO(data))
        if desc:
            header["description"] = desc.strip()
    except Exception:
        # Fallback parse 'desc' tag if ImageCms fails
        pass

    return header


def extract_color_profiles(
    pike_doc: Optional[pikepdf.Pdf],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Extracts ICC color profiles into `output_dir / "profiles"` and lists spot colors.
    When `output_dir` is None, inspects ICC headers and spot inks in memory without writing files.
    """
    write_files = output_dir is not None
    profiles_dir = (output_dir / "profiles") if write_files else None
    if profiles_dir is not None:
        profiles_dir.mkdir(parents=True, exist_ok=True)

    extracted_profiles: List[Dict[str, Any]] = []
    seen_hashes: Set[str] = set()
    spot_colors: Set[str] = set()

    if not pike_doc:
        return {"profiles": [], "spot_colors": []}

    profile_counter = 1

    # 1. Scan all stream objects for ICC magic 'acsp' at offset 36
    for idx, obj in enumerate(pike_doc.objects):
        if not isinstance(obj, pikepdf.Stream):
            continue

        try:
            raw_bytes = obj.read_bytes()
        except Exception:
            continue

        if len(raw_bytes) >= 40 and raw_bytes[36:40] == b"acsp":
            sha = compute_sha256(raw_bytes)
            if sha in seen_hashes:
                continue
            seen_hashes.add(sha)

            header_info = _parse_icc_header(raw_bytes)
            safe_desc = sanitize_filename(header_info["description"], max_length=50, fallback=f"profile_{profile_counter}")
            filename = f"profile_{profile_counter:02d}_{safe_desc}.icc"

            if write_files and profiles_dir is not None:
                profile_path = profiles_dir / filename
                try:
                    with open(profile_path, "wb") as f:
                        f.write(raw_bytes)
                except Exception:
                    continue

            file_size = len(raw_bytes)
            extracted_profiles.append({
                "id": profile_counter,
                "filename": f"profiles/{filename}",
                "description": header_info["description"],
                "color_space": header_info["color_space"],
                "connection_space": header_info["connection_space"],
                "device_class": header_info["device_class"],
                "version": header_info["version"],
                "file_size": format_bytes(file_size),
                "file_size_bytes": file_size,
                "sha256": sha,
            })
            profile_counter += 1

    # 2. Extract spot colors and separation names from ColorSpaces
    def inspect_colorspace(cs_obj):
        try:
            if isinstance(cs_obj, pikepdf.Array) and len(cs_obj) >= 2:
                cs_type = str(cs_obj[0])
                if cs_type == "/Separation":
                    colorant = str(cs_obj[1]).lstrip("/")
                    if colorant.lower() not in STANDARD_PROCESS_INKS:
                        spot_colors.add(colorant)
                elif cs_type == "/DeviceN" and len(cs_obj) >= 2:
                    colorants = cs_obj[1]
                    if isinstance(colorants, pikepdf.Array):
                        for c in colorants:
                            c_name = str(c).lstrip("/")
                            if c_name.lower() not in STANDARD_PROCESS_INKS:
                                spot_colors.add(c_name)
        except Exception:
            pass

    try:
        # Check OutputIntents
        if hasattr(pike_doc, "Root") and "/OutputIntents" in pike_doc.Root:
            for intent in pike_doc.Root.OutputIntents:
                if "/OutputConditionIdentifier" in intent:
                    cond_id = str(intent.OutputConditionIdentifier)
                    # Often contains standard e.g. "FOGRA39" or "CGATS TR 001"
                    pass

        # Check pages resources for ColorSpace
        for page in pike_doc.pages:
            if "/Resources" in page:
                res = page.Resources
                if "/ColorSpace" in res:
                    cs_dict = res.ColorSpace
                    if isinstance(cs_dict, pikepdf.Dictionary):
                        for cs_name, cs_val in cs_dict.items():
                            inspect_colorspace(cs_val)
                    elif isinstance(cs_dict, pikepdf.Array):
                        inspect_colorspace(cs_dict)
    except Exception:
        pass

    return {
        "profiles": extracted_profiles,
        "spot_colors": sorted(list(spot_colors)),
    }
