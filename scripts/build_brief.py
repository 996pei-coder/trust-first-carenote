"""Build the standalone diagrams and three-page technical brief PDF."""

from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent.parent
DIAGRAM_DIR = ROOT / "docs" / "diagrams"
OUTPUT_DIR = ROOT / "output" / "pdf"
ARCHITECTURE_PATH = DIAGRAM_DIR / "architecture.png"
DATA_MODEL_PATH = DIAGRAM_DIR / "data-model.png"
PDF_PATH = OUTPUT_DIR / "trust-first-carenote-technical-brief.pdf"

INK = "#17251f"
MUTED = "#617168"
GREEN = "#176b4d"
GREEN_SOFT = "#e6f2ec"
AMBER = "#a45c14"
AMBER_SOFT = "#fff2df"
RED = "#a23b32"
RED_SOFT = "#fbeae7"
LINE = "#cbd8cf"
PAPER = "#f7f8f5"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def rounded_box(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    title: str,
    lines: Sequence[str],
    fill: str = "#ffffff",
    outline: str = LINE,
    accent: str = GREEN,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=20, fill=fill, outline=outline, width=3)
    draw.rounded_rectangle((x1, y1, x1 + 12, y2), radius=6, fill=accent)
    draw.text((x1 + 30, y1 + 22), title, font=font(28, True), fill=INK)
    y = y1 + 64
    for line in lines:
        draw.text((x1 + 30, y), line, font=font(20), fill=MUTED)
        y += 29


def arrow(
    draw: ImageDraw.ImageDraw,
    start: Tuple[int, int],
    end: Tuple[int, int],
    label: str = "",
) -> None:
    draw.line((start, end), fill=GREEN, width=5)
    ex, ey = end
    sx, sy = start
    if abs(ex - sx) >= abs(ey - sy):
        direction = 1 if ex > sx else -1
        points = [(ex, ey), (ex - 15 * direction, ey - 10), (ex - 15 * direction, ey + 10)]
    else:
        direction = 1 if ey > sy else -1
        points = [(ex, ey), (ex - 10, ey - 15 * direction), (ex + 10, ey - 15 * direction)]
    draw.polygon(points, fill=GREEN)
    if label:
        mx, my = (sx + ex) // 2, (sy + ey) // 2
        label_font = font(16, True)
        text_box = draw.textbbox((0, 0), label, font=label_font)
        label_width = text_box[2] - text_box[0] + 22
        label_height = text_box[3] - text_box[1] + 14
        draw.rounded_rectangle(
            (
                mx - label_width // 2,
                my - label_height // 2,
                mx + label_width // 2,
                my + label_height // 2,
            ),
            radius=8,
            fill="#ffffff",
        )
        draw.text((mx, my), label, anchor="mm", font=label_font, fill=GREEN)


def build_architecture() -> None:
    image = PILImage.new("RGB", (1600, 860), PAPER)
    draw = ImageDraw.Draw(image)
    draw.text((70, 45), "Trust-first CareNote architecture", font=font(40, True), fill=INK)
    draw.text(
        (70, 100),
        "One trust boundary, explicit policies, synthetic data only",
        font=font(22),
        fill=MUTED,
    )
    rounded_box(
        draw,
        (70, 190, 390, 460),
        "Care team UI",
        ["Jinja2 + CSS", "Top Card + timeline", "Patient-safe view", "Role demo selector"],
        fill="#ffffff",
    )
    rounded_box(
        draw,
        (500, 160, 1080, 500),
        "FastAPI trust boundary",
        [
            "Clinic/patient scope + RBAC",
            "Version, audit, conflict, provenance",
            "Importance + bounded feedback",
            "PHI redaction before AI adapter",
        ],
        fill=GREEN_SOFT,
    )
    rounded_box(
        draw,
        (1190, 190, 1515, 460),
        "SQLite trust graph",
        ["Entries + versions", "Comments + highlights", "Conflicts + audit", "Redacted sources only"],
    )
    rounded_box(
        draw,
        (500, 610, 870, 790),
        "Deterministic scribe",
        ["Receives redacted text", "Repeatable local draft"],
        fill=AMBER_SOFT,
        accent=AMBER,
    )
    rounded_box(
        draw,
        (970, 610, 1340, 790),
        "Production replacements",
        ["OIDC + encrypted DB", "TLS + monitoring"],
        fill=RED_SOFT,
        accent=RED,
    )
    arrow(draw, (390, 325), (500, 325), "HTTP")
    arrow(draw, (1080, 325), (1190, 325), "SQL")
    arrow(draw, (720, 500), (720, 610), "redacted only")
    draw.line((1080, 500, 1155, 610), fill=RED, width=4)
    draw.text((1120, 555), "deployment", anchor="mm", font=font(17, True), fill=RED)
    image.save(ARCHITECTURE_PATH, quality=95)


def entity_box(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    title: str,
    fields: Sequence[str],
    color: str = GREEN,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=16, fill="#ffffff", outline=color, width=3)
    draw.rounded_rectangle((x1, y1, x2, y1 + 48), radius=16, fill=color)
    draw.rectangle((x1, y1 + 31, x2, y1 + 48), fill=color)
    draw.text((x1 + 16, y1 + 24), title, anchor="lm", font=font(23, True), fill="#ffffff")
    y = y1 + 65
    for field in fields:
        draw.text((x1 + 16, y), field, font=font(16), fill=INK)
        y += 22


def build_data_model() -> None:
    image = PILImage.new("RGB", (1800, 1150), PAPER)
    draw = ImageDraw.Draw(image)
    draw.text((60, 35), "Relational trust graph", font=font(38, True), fill=INK)
    draw.text((60, 86), "Arrows point from parent/source to dependent evidence", font=font(21), fill=MUTED)

    boxes = {
        "Clinic": (60, 160, 340, 330),
        "User": (430, 160, 710, 350),
        "Patient": (800, 150, 1100, 370),
        "TopicWeight": (1190, 160, 1510, 350),
        "AuditEvent": (1560, 160, 1750, 350),
        "Entry": (650, 480, 1080, 780),
        "SourceArtifact": (60, 510, 390, 750),
        "EntryVersion": (1150, 470, 1480, 720),
        "Comment": (1510, 470, 1750, 720),
        "Highlight": (520, 890, 850, 1100),
        "Conflict": (960, 890, 1290, 1100),
    }
    entity_box(draw, boxes["Clinic"], "Clinic", ["id", "name"])
    entity_box(draw, boxes["User"], "User", ["clinic_id", "role", "display_name"])
    entity_box(draw, boxes["Patient"], "Patient", ["clinic_id", "user_id", "synthetic", "MRN + DOB"])
    entity_box(draw, boxes["TopicWeight"], "TopicWeight", ["clinic_id + topic", "bounded weight", "feedback_count"], AMBER)
    entity_box(draw, boxes["AuditEvent"], "Audit", ["actor/action", "object/version", "field names only"], RED)
    entity_box(
        draw,
        boxes["Entry"],
        "Entry",
        [
            "patient + author role",
            "type + visibility + section",
            "content + version",
            "fact key/value",
            "session + provenance pointer",
        ],
    )
    entity_box(draw, boxes["SourceArtifact"], "SourceArtifact", ["patient + session", "interaction type", "redacted text", "redacted hash"], AMBER)
    entity_box(draw, boxes["EntryVersion"], "EntryVersion", ["entry + version", "full snapshot", "changed_by", "reason + time"])
    entity_box(draw, boxes["Comment"], "Comment", ["entry + author", "mention/assignee", "resolved"])
    entity_box(draw, boxes["Highlight"], "Highlight", ["entry + exact span", "risk reason + topic", "status + score", "provenance"])
    entity_box(draw, boxes["Conflict"], "Conflict", ["earlier + later entry", "review status", "authoritative entry"], RED)

    arrow(draw, (340, 245), (430, 245), "1:N")
    arrow(draw, (710, 255), (800, 255), "1:1 patient")
    arrow(draw, (1100, 240), (1190, 240), "clinic learning")
    arrow(draw, (975, 370), (870, 480), "1:N entries")
    arrow(draw, (800, 370), (390, 560), "redacted sources")
    arrow(draw, (1080, 600), (1150, 600), "snapshots")
    arrow(draw, (1080, 650), (1510, 650), "comments")
    arrow(draw, (790, 780), (685, 890), "highlights")
    arrow(draw, (960, 780), (1100, 890), "conflicts")
    draw.line((1480, 270, 1610, 350), fill=RED, width=4)
    draw.text((1540, 310), "metadata", anchor="mm", font=font(16, True), fill=RED)
    image.save(DATA_MODEL_PATH, quality=95)


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def bullets(items: Iterable[str], style: ParagraphStyle) -> List[Paragraph]:
    return [Paragraph(f"- {item}", style) for item in items]


def page_frame(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#d7e1da"))
    canvas.line(18 * mm, 15 * mm, width - 18 * mm, 15 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.drawString(18 * mm, 9.5 * mm, "Trust-first CareNote | Nightingale 72 Hour Build")
    canvas.drawRightString(width - 18 * mm, 9.5 * mm, f"Peiheng Li | {doc.page}")
    canvas.restoreState()


def build_pdf() -> None:
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25,
        leading=28, textColor=colors.HexColor(INK), spaceAfter=5, alignment=TA_LEFT,
    )
    subtitle = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=9.2,
        leading=13, textColor=colors.HexColor(MUTED), spaceAfter=10,
    )
    h1 = ParagraphStyle(
        "H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14,
        leading=16, textColor=colors.HexColor(GREEN), spaceBefore=5, spaceAfter=5,
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.2,
        leading=12, textColor=colors.HexColor(INK), spaceBefore=4, spaceAfter=3,
    )
    body = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.15,
        leading=10.6, textColor=colors.HexColor(INK), spaceAfter=4,
    )
    small = ParagraphStyle(
        "Small", parent=body, fontSize=7.2, leading=9.2, textColor=colors.HexColor(MUTED),
    )
    bullet = ParagraphStyle(
        "Bullet", parent=body, leftIndent=9, firstLineIndent=-7, spaceAfter=2.4,
    )
    callout = ParagraphStyle(
        "Callout", parent=body, fontName="Helvetica-Bold", fontSize=9.2, leading=12,
        textColor=colors.HexColor(GREEN),
    )

    document = SimpleDocTemplate(
        str(PDF_PATH), pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm,
        topMargin=14 * mm, bottomMargin=20 * mm,
        title="Trust-first CareNote - Technical Brief",
        author="Peiheng Li",
        subject="Nightingale 72 Hour Build",
    )
    story = []

    story.extend([
        para("TRUST-FIRST CARENOTE", title),
        para("Nightingale 72 Hour Build - Technical Brief | Peiheng Li", subtitle),
        Table(
            [[para("A 10-second clinical brief is only useful when every claim can be traced, challenged, and corrected without weakening role boundaries.", callout)]],
            colWidths=[176 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(GREEN_SOFT)),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#b7d3c3")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]),
        ),
        Spacer(1, 5),
        para("1. Product decision", h1),
        para(
            "EHR tables hold snapshots, but care teams reason from the story between them. CareNote treats the longitudinal timeline as the source of truth and the Top Card as a small derived view - never a summary that can silently drift.",
            body,
        ),
    ])
    story.extend(bullets([
        "Glanceability: five or fewer ranked items show risk, open work, context, and a short reason.",
        "Trust: every highlight resolves to an exact entry and character span; conflicts stay visible until reviewed.",
        "Safe collaboration: server-side patient/staff/clinician/admin rules prevent cross-role overwrite and patient exposure to internal comments or raw AI notes.",
    ], bullet))
    story.extend([
        para("2. Architecture", h1),
        Image(str(ARCHITECTURE_PATH), width=176 * mm, height=94.6 * mm),
        para(
            "The browser does not decide authorization. Each protected request checks actor role, clinic scope, patient ownership, entry visibility, and role-owned writes. X-User-ID selects a seeded demo identity only; production replaces it with verified OIDC while retaining the policies.",
            small,
        ),
        PageBreak(),
        para("DATA, VERSIONS, AND PROVENANCE", title),
        para("A relational trust graph keeps content, evidence, collaboration, and learning connected.", subtitle),
        Image(str(DATA_MODEL_PATH), width=176 * mm, height=112.4 * mm),
        para("3. Trust flows", h1),
    ])
    flow_table = Table(
        [
            [para("AI scribe", h2), para("Redact known/labelled names, IC/FIN, phone, and email; persist only the redacted source; pass only redacted text to the deterministic adapter; save a distinct system entry with session provenance.", body)],
            [para("Edit + revert", h2), para("Require expected_version. A match creates a full immutable snapshot and metadata-only audit event. A stale same-entry write returns 409. Revert restores a snapshot as a new version.", body)],
            [para("Highlight", h2), para("The server derives text from validated character bounds. The pointer resolver rechecks scope, visibility, entry identity, and span bounds before returning the exact substring.", body)],
            [para("Conflict", h2), para("Different structured values from patient/system and clinician sources create a review object. Nothing is silently overwritten; clinician/admin explicitly selects the authoritative entry.", body)],
        ],
        colWidths=[31 * mm, 145 * mm],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor(LINE)),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(GREEN_SOFT)),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]),
    )
    story.extend([
        flow_table,
        Spacer(1, 4),
        para("4. Explainable importance", h1),
        para(
            "Score = risk + recency + unresolved + review status + bounded topic weight. Pin/accept/reject change the visible status and update clinic topic feedback by +8/+4/-6; a clinician comment on an AI topic adds +1. Topic learning is visible and bounded from -20 to +30, so adaptation cannot become an opaque or runaway model.",
            body,
        ),
        PageBreak(),
        para("SECURITY, EVIDENCE, AND TRADE-OFFS", title),
        para("The prototype makes narrow claims and shows the evidence behind each one.", subtitle),
        para("5. Security and privacy", h1),
    ])
    story.extend(bullets([
        "Clinic-scoped RBAC is enforced in FastAPI; out-of-scope records return 404 to avoid confirming existence.",
        "Patients cannot retrieve internal comments, clinical Top Card data, or raw AI-scribed entries.",
        "Audit events contain actor, action, object, versions, changed field names, and time - never note bodies.",
        "All repository data is fictional and labelled synthetic. The raw scribe transcript is never stored.",
    ], bullet))
    story.extend([
        para("6. Performance evidence", h1),
        Table(
            [["P50", "P95", "P99", "Max", "Target"], ["1.83 ms", "2.09 ms", "2.28 ms", "12.21 ms", "<= 300 ms"]],
            colWidths=[35.2 * mm] * 5,
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(GREEN)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor(LINE)),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]),
        ),
        para(
            "Darwin arm64, Python 3.9.6; 20 warm-ups and 300 in-process authenticated Top Card requests. Includes routing, RBAC, SQLite, ranking, and serialization. Excludes TLS, network, browser rendering, concurrent production load, and managed-database latency; it is an approximation, not a production SLO.",
            small,
        ),
        para("7. Automated evidence", h1),
    ])
    test_rows = [
        ["RBAC scope", "Cross-role writes, patient-safe output, clinic isolation"],
        ["Revision history", "Version increment, diff, revert, metadata-only audit"],
        ["Provenance", "Every Top Card highlight resolves to exact source text"],
        ["Concurrent edits", "Independent sections succeed; stale same-entry write is 409"],
        ["Self-learning", "Pin feedback raises subsequent same-topic suggestion by 8"],
        ["Full suite", "22 passing tests; warm P95 gate <= 300 ms"],
    ]
    story.append(Table(
        [[para(a, h2), para(b, body)] for a, b in test_rows],
        colWidths=[45 * mm, 131 * mm],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f2f5f1")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(LINE)),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]),
    ))
    story.extend([
        para("8. Trade-offs and next steps", h1),
        para(
            "I chose a working trust loop over voice capture, real EHR integration, CRDT editing, or an opaque ML model. SQLite and header-selected demo identity are prototype choices, not production security claims. Next: verified OIDC, encrypted managed PostgreSQL with defense-in-depth row policies, schema migrations, retention/backups, security monitoring, clinical workflow testing, then structured extraction and voice capture behind the same redaction and provenance boundary.",
            body,
        ),
        KeepTogether([
            Spacer(1, 3),
            Table(
                [[para("Scope statement", h2), para("Synthetic data only. No external AI model, EHR, audio, or real patient information is used.", body)]],
                colWidths=[35 * mm, 141 * mm],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(AMBER_SOFT)),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#dfbd90")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]),
            ),
        ]),
    ])

    document.build(story, onFirstPage=page_frame, onLaterPages=page_frame)


def main() -> None:
    DIAGRAM_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    build_architecture()
    build_data_model()
    build_pdf()
    print(PDF_PATH)


if __name__ == "__main__":
    main()
