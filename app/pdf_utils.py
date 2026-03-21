from __future__ import annotations

from io import BytesIO
from pathlib import Path
from datetime import datetime

import pandas as pd
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = A4
APP_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = APP_DIR / "assets"
DATA_DIR = APP_DIR / "data"
PDF_DIR = DATA_DIR / "generated_pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATE_CANDIDATES = [
    ASSETS_DIR / "skierowanie_template.pdf",
    ASSETS_DIR / "skierowanie-na-badania-lekarskie-wstepneokresowekontrolne.pdf",
    APP_DIR / "skierowanie_template.pdf",
    APP_DIR / "skierowanie-na-badania-lekarskie-wstepneokresowekontrolne.pdf",
]

CATEGORY_TO_SECTION = {
    "CZYNNIKI FIZYCZNE": "I",
    "PYŁY": "II",
    "CZYNNIKI CHEMICZNE": "III",
    "CZYNNIKI BIOLOGICZNE": "IV",
    "INNE": "V",
}


def _find_template() -> Path | None:
    for p in TEMPLATE_CANDIDATES:
        if p.exists():
            return p
    return None


def _register_fonts() -> tuple[str, str]:
    regular_candidates = [
        Path("C:/Windows/Fonts/times.ttf"),
        Path("C:/Windows/Fonts/georgia.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
    ]
    bold_candidates = [
        Path("C:/Windows/Fonts/timesbd.ttf"),
        Path("C:/Windows/Fonts/georgiab.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf"),
    ]

    regular = "Times-Roman"
    bold = "Times-Bold"

    for fp in regular_candidates:
        if fp.exists():
            try:
                pdfmetrics.registerFont(TTFont("APP_REGULAR", str(fp)))
                regular = "APP_REGULAR"
                break
            except Exception:
                pass

    for fp in bold_candidates:
        if fp.exists():
            try:
                pdfmetrics.registerFont(TTFont("APP_BOLD", str(fp)))
                bold = "APP_BOLD"
                break
            except Exception:
                pass

    return regular, bold


def _fmt_date(value) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        if "T" in value:
            value = value.split("T")[0]
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(value, fmt).strftime("%d.%m.%Y")
            except Exception:
                pass
        try:
            return datetime.fromisoformat(value).strftime("%d.%m.%Y")
        except Exception:
            return value
    try:
        return value.strftime("%d.%m.%Y")
    except Exception:
        return str(value)


def _wrap_text(text: str, font_name: str, font_size: int, max_width: float) -> list[str]:
    words = str(text or "").split()
    if not words:
        return []

    lines: list[str] = []
    current = words[0]

    for word in words[1:]:
        test = f"{current} {word}"
        if stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def _draw_lines(
    c: canvas.Canvas,
    text: str,
    x: float,
    y_top: float,
    width: float,
    font_name: str,
    font_size: int,
    line_gap: float,
    max_lines: int,
):
    c.setFont(font_name, font_size)
    lines = _wrap_text(text, font_name, font_size, width)[:max_lines]
    for i, line in enumerate(lines):
        c.drawString(x, y_top - i * line_gap, line)


def _draw_centered(
    c: canvas.Canvas,
    text: str,
    x1: float,
    x2: float,
    y: float,
    font_name: str,
    font_size: int,
):
    text = str(text or "")
    c.setFont(font_name, font_size)
    w = stringWidth(text, font_name, font_size)
    x = x1 + ((x2 - x1) - w) / 2
    c.drawString(x, y, text)


def _strike_unused_exam_types(
    c: canvas.Canvas,
    exam_type: str,
    font_name: str,
    font_size: int,
):
    """
    Przekreślenia na napisie:
    (wstępne/okresowe/kontrolne*)
    """
    c.setFont(font_name, font_size)

    # dobrane pod wzór strony 1
    positions = {
        "wstępne": (254, PAGE_H - 112),
        "okresowe": (322, PAGE_H - 112),
        "kontrolne": (392, PAGE_H - 112),
    }

    for label, (x, y) in positions.items():
        if label != exam_type:
            w = stringWidth(label, font_name, font_size)
            c.line(x, y + 3, x + w, y - 3)


def _extract_hazards(referral: dict) -> pd.DataFrame:
    raw = referral.get("hazards")

    if isinstance(raw, pd.DataFrame):
        df = raw.copy()
    elif isinstance(raw, list):
        df = pd.DataFrame(raw)
    else:
        df = pd.DataFrame()

    if df.empty:
        return pd.DataFrame(columns=["hazard_name", "category", "section_label"])

    rename_map = {
        "Zagrożenie": "hazard_name",
        "hazard": "hazard_name",
        "Kategoria": "category",
        "Sekcja": "section_label",
    }
    df = df.rename(columns=rename_map)

    for col in ["hazard_name", "category", "section_label"]:
        if col not in df.columns:
            df[col] = ""

    df["hazard_name"] = df["hazard_name"].fillna("").astype(str).str.strip()
    df["category"] = df["category"].fillna("").astype(str).str.strip().str.upper()
    df["section_label"] = df["section_label"].fillna("").astype(str).str.strip()

    df = df[df["hazard_name"] != ""].copy()

    if df.empty:
        return df

    missing = df["section_label"] == ""
    df.loc[missing, "section_label"] = df.loc[missing, "category"].map(CATEGORY_TO_SECTION).fillna("V")

    df["section_label"] = df["section_label"].replace(
        {
            "I. Czynniki fizyczne": "I",
            "II. Pyły": "II",
            "III. Czynniki chemiczne": "III",
            "IV. Czynniki biologiczne": "IV",
            "V. Inne czynniki, w tym niebezpieczne": "V",
        }
    )

    return df


def _group_hazards_by_section(referral: dict) -> dict[str, str]:
    df = _extract_hazards(referral)
    result = {k: "" for k in ["I", "II", "III", "IV", "V"]}

    if df.empty:
        return result

    for section in result:
        vals = df[df["section_label"] == section]["hazard_name"].tolist()
        result[section] = "; ".join(v for v in vals if str(v).strip())

    return result


def generate_referral_pdf(referral: dict) -> str:
    font_reg, font_bold = _register_fonts()
    template_path = _find_template()

    referral_number = str(referral.get("referral_number", f"ref_{datetime.now().strftime('%Y%m%d%H%M%S')}"))
    safe_name = referral_number.replace("/", "-").replace("\\", "-")
    out_path = PDF_DIR / f"{safe_name}.pdf"

    employee_name = str(referral.get("employee_name", "") or "")
    position_name = str(referral.get("position_name", "") or "")
position_description = str(referral.get("position_description", "") or position_name)
    employer = str(referral.get("employer", "") or "SAFETY Service")
    pesel = str(referral.get("pesel", "") or "-")
    employee_address = str(referral.get("employee_address", "") or "-")
    place_of_issue = str(referral.get("place_of_issue", "") or "Warszawa")
    issue_date = _fmt_date(referral.get("issue_date"))
    exam_type = str(referral.get("exam_type", "okresowe") or "okresowe").strip().lower()

    grouped = _group_hazards_by_section(referral)
    total_hazards = len(_extract_hazards(referral))

    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)

    # ---------------------------
    # STRONA 1 - overlay na wzór
    # ---------------------------

    # Oznaczenie pracodawcy
    _draw_centered(c, employer, 95, 235, PAGE_H - 43, font_reg, 11)

    # Miejscowość i data
    _draw_centered(c, f"{place_of_issue} {issue_date}", 390, 530, PAGE_H - 43, font_reg, 11)

    # Przekreślenie niewybranych typów badań
    _strike_unused_exam_types(c, exam_type, font_bold, 13)

    # Akapit wprowadzający
    intro = (
        "Działając na podstawie art. 229 § 4a ustawy z dnia 26 czerwca 1974 r. – "
        "Kodeks pracy (Dz. U. z 2022 r. poz. 1510, z późn. zm.), kieruję na badania lekarskie:"
    )
    _draw_lines(c, intro, 70, PAGE_H - 170, 465, font_reg, 10, 13, 3)

    # Imię i nazwisko
    _draw_centered(c, employee_name, 155, 535, PAGE_H - 233, font_reg, 11)

    # PESEL
    _draw_centered(c, pesel, 155, 535, PAGE_H - 264, font_reg, 11)

    # Adres
    _draw_centered(c, employee_address, 188, 535, PAGE_H - 296, font_reg, 10)

    # Stanowisko / stanowiska pracy - 2 linie
    _draw_lines(c, position_name, 170, PAGE_H - 351, 360, font_reg, 10, 14, 2)

    # Określenie stanowiska pracy - 3 linie
    _draw_lines(c, position_description, 275, PAGE_H - 408, 260, font_reg, 10, 15, 3)

    # Sekcje I-V na stronie 1
    _draw_lines(c, grouped["I"] or "-",   165, PAGE_H - 584, 350, font_reg, 10, 12, 2)
    _draw_lines(c, grouped["II"] or "-",  165, PAGE_H - 616, 350, font_reg, 10, 12, 2)
    _draw_lines(c, grouped["III"] or "-", 165, PAGE_H - 648, 350, font_reg, 10, 12, 2)
    _draw_lines(c, grouped["IV"] or "-",  165, PAGE_H - 680, 350, font_reg, 10, 12, 2)
    _draw_lines(c, grouped["V"] or "-",   165, PAGE_H - 712, 350, font_reg, 10, 12, 2)

    # Łączna liczba czynników - w prostokącie
    _draw_centered(c, str(total_hazards), 455, 515, PAGE_H - 768, font_reg, 12)

    c.save()
    packet.seek(0)

    if template_path and template_path.exists():
        overlay_reader = PdfReader(packet)
        template_reader = PdfReader(str(template_path))
        writer = PdfWriter()

        # nakładamy tylko stronę 1, a resztę stron wzoru zostawiamy bez zmian
        for i, base_page in enumerate(template_reader.pages):
            if i == 0 and len(overlay_reader.pages) > 0:
                base_page.merge_page(overlay_reader.pages[0])
            writer.add_page(base_page)

        with open(out_path, "wb") as f:
            writer.write(f)
    else:
        with open(out_path, "wb") as f:
            f.write(packet.getvalue())

    return str(out_path)