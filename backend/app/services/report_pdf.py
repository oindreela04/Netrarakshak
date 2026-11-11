"""Hospital-quality PDF screening report (ReportLab).

Approval status is derived ONLY from a signed ClinicalReview row. A report without a signature is rendered with a
"DRAFT — NOT CLINICIAN APPROVED" watermark and status.
"""
import io
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

from ..models import ClinicalReview, Hospital, Screening
from ..serializers import latest_ai
from ..storage import get_storage

IST = ZoneInfo("Asia/Kolkata")
NAVY = colors.HexColor("#0B1F3A")
TEAL = colors.HexColor("#3E8E8A")
BLUE = colors.HexColor("#1F6FB2")
MUTED = colors.HexColor("#5B6B7F")
LINE = colors.HexColor("#D7DEE8")
SOFT = colors.HexColor("#F3F6FA")
AMBER = colors.HexColor("#B26B00")
RED = colors.HexColor("#B42318")

GRADE_LABEL = {"no_dr": "No apparent diabetic retinopathy", "mild_npdr": "Mild NPDR", "moderate_npdr": "Moderate NPDR",
               "severe_npdr": "Severe NPDR", "proliferative_dr": "Proliferative DR", "ungradable": "Ungradable",
               "not_assessed": "Not assessed"}
DECISION_LABEL = {"accept": "Accepted AI suggestion", "modify": "Modified AI suggestion", "reject": "Rejected AI suggestion",
                  "not_applicable": "No AI finding available"}

ss = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, textColor=NAVY, leading=18),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.5, textColor=NAVY, spaceBefore=8, spaceAfter=4, leading=13),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=8.8, leading=12, textColor=colors.HexColor("#1B2633")),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=7.4, leading=9.6, textColor=MUTED),
    "label": ParagraphStyle("label", fontName="Helvetica", fontSize=7.2, leading=9, textColor=MUTED),
    "value": ParagraphStyle("value", fontName="Helvetica-Bold", fontSize=8.8, leading=11, textColor=colors.HexColor("#1B2633")),
    "cap": ParagraphStyle("cap", fontName="Helvetica-Oblique", fontSize=7.2, leading=9, textColor=MUTED, alignment=TA_LEFT),
}


def _p(t, s="body"):
    return Paragraph(str(t).replace("\n", "<br/>"), ss[s])


def _esc(t) -> str:
    return (str(t or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ist(dt):
    if not dt:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).strftime("%d %b %Y, %H:%M IST")


def _img(data: bytes, w: float):
    from PIL import Image as PILImage
    import cv2
    from .quality import decode_image
    bgr = decode_image(data)
    h0, w0 = bgr.shape[:2]
    scale = 900 / max(h0, w0)
    if scale < 1:
        bgr = cv2.resize(bgr, (int(w0 * scale), int(h0 * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 88])
    PILImage  # noqa
    h1, w1 = bgr.shape[:2]
    return Image(io.BytesIO(buf.tobytes()), width=w, height=w * h1 / w1)


def build_report(screening: Screening, hospital: Hospital, report_number: str, generated_by_name: str) -> tuple[bytes, str]:
    store = get_storage()
    p = screening.patient
    signed: ClinicalReview | None = next((r for r in reversed(screening.reviews) if r.status == "signed"), None)
    recapture = next((r for r in reversed(screening.reviews) if r.recapture_requested), None)
    if signed:
        status = "CLINICIAN APPROVED"
    elif recapture:
        status = "RECAPTURE REQUESTED — NOT APPROVED"
    else:
        status = "DRAFT — PENDING CLINICIAN REVIEW"
    brand = colors.HexColor(hospital.brand_color or "#0B1F3A")
    now = datetime.now(timezone.utc)

    buf = io.BytesIO()
    W, H = A4
    margin = 16 * mm
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=margin, rightMargin=margin, topMargin=34 * mm, bottomMargin=20 * mm,
                          title=f"Retinal Screening Report {report_number}", author=hospital.name,
                          subject="NetraRakshak retinal screening report", creator="NetraRakshak")

    logo = None
    if hospital.logo_key:
        try:
            logo = store.get(hospital.logo_key)
        except Exception:
            logo = None

    def chrome(c, d):
        c.saveState()
        c.setFillColor(brand)
        c.rect(0, H - 24 * mm, W, 24 * mm, fill=1, stroke=0)
        c.setFillColor(TEAL)
        c.rect(0, H - 25.2 * mm, W, 1.2 * mm, fill=1, stroke=0)
        x = margin
        if logo:
            try:
                from reportlab.lib.utils import ImageReader
                c.drawImage(ImageReader(io.BytesIO(logo)), x, H - 20 * mm, width=16 * mm, height=16 * mm,
                            preserveAspectRatio=True, mask="auto")
                x += 19 * mm
            except Exception:
                pass
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 13.5)
        c.drawString(x, H - 11.5 * mm, hospital.name[:70])
        c.setFont("Helvetica", 7.8)
        sub = hospital.report_header or ", ".join(v for v in (hospital.address, hospital.city, hospital.state) if v)
        c.drawString(x, H - 16.5 * mm, sub[:120])
        if hospital.phone or hospital.email:
            c.drawString(x, H - 20.3 * mm, "  ·  ".join(v for v in (hospital.phone, hospital.email) if v)[:120])
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(W - margin, H - 11.5 * mm, "RETINAL SCREENING REPORT")
        c.setFont("Helvetica", 7.6)
        c.drawRightString(W - margin, H - 16.5 * mm, f"Report {report_number}")
        c.drawRightString(W - margin, H - 20.3 * mm, f"Page {d.page}")
        # footer
        c.setStrokeColor(LINE)
        c.line(margin, 15 * mm, W - margin, 15 * mm)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.6)
        c.drawString(margin, 11 * mm, "AI-assisted screening output for review by a qualified ophthalmologist. Not a standalone diagnosis. "
                                      "NetraRakshak is not clinically validated or regulatory-approved.")
        c.drawString(margin, 7.6 * mm, (hospital.report_footer or "")[:160])
        c.drawRightString(W - margin, 7.6 * mm, f"Generated {_ist(now)} · NetraRakshak")
        c.restoreState()

    def watermark(c, d):
        marks = []
        if not signed:
            marks.append("DRAFT — NOT CLINICIAN APPROVED")
        if p.is_synthetic:
            marks.append("SYNTHETIC TEST DATA")
        for k, m in enumerate(marks):
            c.saveState()
            c.setFillColor(colors.Color(0.7, 0.1, 0.1, alpha=0.09))
            c.setFont("Helvetica-Bold", 40 if k == 0 else 34)
            c.translate(W / 2, H / 2 - k * 70)
            c.rotate(32)
            c.drawCentredString(0, 0, m)
            c.restoreState()

    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(margin, 20 * mm, W - 2 * margin, H - 54 * mm, id="f")], onPage=chrome, onPageEnd=watermark)])
    cw = W - 2 * margin
    story = []

    # Status banner
    sc = TEAL if signed else (RED if recapture else AMBER)
    banner = Table([[_p(f"<font color='white'><b>REVIEW STATUS: {status}</b></font>"),
                     _p(f"<font color='white'>Screening date: {_ist(screening.created_at)}</font>")]],
                   colWidths=[cw * 0.58, cw * 0.42])
    banner.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), sc), ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                                ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7)]))
    story += [banner, Spacer(1, 6)]
    if p.is_synthetic:
        story.append(_p("<font color='#B42318'><b>Synthetic test patient.</b> This report was produced with "
                        "artificially generated data for software testing and has no clinical meaning.</font>"))

    # Patient block
    def kv(label, value):
        return [_p(label, "label"), _p(_esc(value) or "—", "value")]
    diab = "Yes" + (f" · {p.diabetes_type}" if p.diabetes_type else "") + (f" · since {p.diabetes_since_year}" if p.diabetes_since_year else "") \
        + (f" · HbA1c {p.last_hba1c}%" if p.last_hba1c else "") if p.has_diabetes else "No"
    htn = ("Yes" + (f" · since {p.hypertension_since_year}" if p.hypertension_since_year else "")) if p.has_hypertension else "No"
    rows = [
        kv("Patient name", p.full_name) + kv("Patient ID", p.patient_code),
        kv("Date of birth / Age", f"{p.date_of_birth:%d %b %Y} · {p.age} y") + kv("Sex", p.sex.capitalize()),
        kv("Diabetes", diab) + kv("Hypertension", htn),
        kv("Screening ID", screening.screening_code) + kv("Camera", screening.camera_device or "Not recorded"),
        kv("Pupil dilation", {True: "Dilated", False: "Undilated", None: "Not recorded"}[screening.dilated]) + kv("Report generated by", generated_by_name),
    ]
    t = Table([[r[0], r[1], r[2], r[3]] for r in rows], colWidths=[cw * 0.17, cw * 0.33, cw * 0.17, cw * 0.33])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5), ("LINEBELOW", (0, 0), (-1, -2), 0.3, LINE)]))
    story += [_p("Patient information", "h2"), t]

    # Images
    images = {i.eye: i for i in screening.images if i.is_current}
    ai = {r.eye: r for r in latest_ai(screening)}
    eye_cols = []
    for eye, tag in (("right", "OD — Right eye"), ("left", "OS — Left eye")):
        img = images.get(eye)
        cell = [_p(f"<b>{tag}</b>", "body"), Spacer(1, 2)]
        if img:
            try:
                cell.append(_img(store.get(img.storage_key), cw * 0.47))
            except Exception:
                cell.append(_p("Image unavailable", "small"))
            q = img.quality or {}
            colr = {"acceptable": "#2E7D5B", "recapture_required": "#B42318", "inconclusive": "#B26B00"}.get(img.quality_verdict, "#5B6B7F")
            cell += [Spacer(1, 3), _p(f"Image quality: <font color='{colr}'><b>{img.quality_verdict.replace('_', ' ').upper()}</b></font>", "body"),
                     _p(_esc(q.get("summary", "")), "small"),
                     _p(f"{img.width}×{img.height}px · {_esc(img.original_filename)} · SHA-256 {img.sha256[:12]}…", "small")]
        else:
            cell.append(_p("No photograph uploaded for this eye.", "small"))
        eye_cols.append(cell)
    ti = Table([eye_cols], colWidths=[cw / 2, cw / 2])
    ti.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [_p("Retinal photographs", "h2"), ti]

    # AI findings
    story.append(_p("AI screening output (unmodified model output)", "h2"))
    hdr = [_p("<b>Eye</b>"), _p("<b>AI result</b>"), _p("<b>Confidence</b>"), _p("<b>Model</b>")]
    data = [hdr]
    for eye in ("right", "left"):
        r = ai.get(eye)
        if not r:
            data.append([_p(eye.capitalize()), _p("AI not run", "small"), _p("—"), _p("—")])
            continue
        verdict = _esc(r.display_verdict)
        if r.status == "completed" and r.is_uncertain:
            verdict += f"<br/><font size=7 color='#5B6B7F'>Top class: {_esc(r.predicted_label)}</font>"
        data.append([_p(eye.capitalize()), _p(f"<b>{verdict}</b><br/><font size=7 color='#5B6B7F'>{_esc(r.explanation)}</font>"),
                     _p(f"{r.confidence:.1%}" if r.confidence is not None else "—"),
                     _p(f"{_esc(r.model_name) or '—'}<br/><font size=7>v{_esc(r.model_version) or '—'}</font>")])
    ta = Table(data, colWidths=[cw * 0.1, cw * 0.56, cw * 0.12, cw * 0.22], repeatRows=1)
    ta.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), SOFT), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                            ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(ta)
    story.append(_p("AI outputs are produced by a model that has not been clinically validated. Confidence values are "
                    "temperature-calibrated model probabilities, not the probability of disease. Uncertain or unsupported "
                    "cases are reported as INCONCLUSIVE — HUMAN REVIEW REQUIRED.", "small"))

    # probabilities detail
    prob_rows = [[_p("<b>Class</b>", "small")] + [_p(f"<b>{e.capitalize()}</b>", "small") for e in ("right", "left")]]
    keys = []
    for r in ai.values():
        keys = list((r.probabilities or {}).keys()) or keys
    for k in keys:
        prob_rows.append([_p(GRADE_LABEL.get(k, k), "small")] +
                         [_p(f"{ai[e].probabilities.get(k, 0):.1%}" if e in ai and ai[e].probabilities else "—", "small") for e in ("right", "left")])
    if keys:
        tp = Table(prob_rows, colWidths=[cw * 0.5, cw * 0.25, cw * 0.25])
        tp.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.4, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
                                ("BACKGROUND", (0, 0), (-1, 0), SOFT), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))
        story += [Spacer(1, 4), tp]

    # Explainability
    cams = [(e, r) for e, r in ai.items() if r.gradcam_key]
    if cams:
        cols = []
        for eye in ("right", "left"):
            r = ai.get(eye)
            if r and r.gradcam_key:
                try:
                    cols.append([_p(f"<b>{eye.capitalize()} eye — Grad-CAM</b>", "small"), _img(store.get(r.gradcam_key), cw * 0.32)])
                except Exception:
                    cols.append([_p("Unavailable", "small")])
            else:
                cols.append([_p(f"{eye.capitalize()} eye — no explainability map", "small")])
        te = Table([cols], colWidths=[cw / 2, cw / 2])
        te.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(KeepTogether([_p("Model explainability (Grad-CAM)", "h2"), te,
                                   _p("Heatmaps indicate image regions that most influenced the model's output. They are a model "
                                      "explainability aid, NOT confirmed lesions or clinical findings.", "cap")]))

    # Clinician interpretation
    if signed:
        story.append(CondPageBreak(60 * mm))
    story.append(_p("Clinician interpretation", "h2"))
    if signed:
        rows = [[_p("<b>Eye</b>"), _p("<b>Final grade (clinician)</b>"), _p("<b>Decision on AI output</b>"), _p("<b>Observations</b>")]]
        for eye in ("right", "left"):
            f = (signed.eye_findings or {}).get(eye)
            if not f:
                continue
            obs = _esc(f.get("observations", ""))
            if f.get("other_findings"):
                obs += f"<br/><i>Other:</i> {_esc(f['other_findings'])}"
            if f.get("macular_oedema_suspected") is not None:
                obs += f"<br/><i>Macular oedema suspected:</i> {'Yes' if f['macular_oedema_suspected'] else 'No'}"
            rows.append([_p(eye.capitalize()), _p(f"<b>{GRADE_LABEL.get(f.get('final_grade'), f.get('final_grade'))}</b>"),
                         _p(DECISION_LABEL.get(f.get("ai_decision"), "")), _p(obs or "—")])
        tc = Table(rows, colWidths=[cw * 0.1, cw * 0.25, cw * 0.22, cw * 0.43], repeatRows=1)
        tc.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), SOFT), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                                ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(tc)
        story.append(Spacer(1, 4))
        if signed.overall_impression:
            story += [_p("<b>Impression</b>"), _p(_esc(signed.overall_impression))]
        story += [Spacer(1, 3), _p("<b>Clinician-approved recommendations</b>"), _p(_esc(signed.recommendations) or "—")]
        ref = "Not required"
        if signed.referral_recommended:
            ref = f"<b>Referral recommended</b> ({_esc(signed.referral_urgency) or 'routine'})" + (f" to {_esc(signed.referral_to)}" if signed.referral_to else "")
        story += [Spacer(1, 3), _p(f"<b>Referral:</b> {ref}")]
        if signed.follow_up_months is not None:
            story.append(_p(f"<b>Next screening:</b> in {signed.follow_up_months} month(s)"))
        sig = Table([[_p(f"<b>Electronically signed by</b><br/>{_esc(signed.reviewer.full_name)}<br/>"
                         f"Reg. No. {_esc(signed.reviewer.medical_registration_no)}", "body"),
                      _p(f"<b>Signed at</b><br/>{_ist(signed.signed_at)}<br/><font size=6.5>Signature hash {signed.signature_hash[:32]}…</font>", "body")]],
                    colWidths=[cw / 2, cw / 2])
        sig.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, TEAL), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF6F5")),
                                 ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story += [Spacer(1, 8), KeepTogether(sig)]
    else:
        msg = "This screening has <b>not been reviewed and signed by an ophthalmologist</b>. It must not be used for clinical decisions."
        if recapture:
            msg = f"The reviewing clinician requested recapture: {_esc(recapture.recapture_reason)}. " + msg
        story.append(_p(f"<font color='#B42318'>{msg}</font>"))

    story += [Spacer(1, 8), _p(f"Report ID {report_number} · Screening {screening.screening_code} · Generated {_ist(now)} · "
                               f"AI module: diabetic retinopathy only (other disease modules not active). This report does not "
                               f"exclude other ocular conditions.", "small")]
    doc.build(story)
    return buf.getvalue(), status
