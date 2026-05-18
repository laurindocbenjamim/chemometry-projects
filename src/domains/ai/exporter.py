import base64
import io
import zipfile
from datetime import datetime
from typing import Dict
import logging

logger = logging.getLogger("exporter")

# Safe imports for ReportLab to support connected environments
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

def generate_zip_archive(plots_data: Dict[str, str]) -> io.BytesIO:
    """
    Decodes base64 plot images and compiles them into a ZIP archive in memory.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for plot_type, base64_str in plots_data.items():
            if not base64_str:
                continue
            # Strip standard browser data-url header if present
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
            img_data = base64.b64decode(base64_str)
            # Create a filesystem safe name for the file inside the zip
            safe_name = plot_type.lower().replace(" ", "_")
            zip_file.writestr(f"{safe_name}_plot.png", img_data)
    zip_buffer.seek(0)
    return zip_buffer

def parse_inline_markdown(text: str) -> str:
    """
    Safely convert double asterisks to ReportLab-friendly bold tags,
    escaping standard XML characters first to avoid ReportLab parser crashes.
    """
    if not text:
        return ""
    import re
    # 1. Escape XML standard entities to prevent syntax crashes
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # 2. Convert double asterisks **bold** to <b>bold</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # 3. Convert single asterisk *italic* to <i>italic</i>
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    # 4. Support standard underscores _italic_
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)
    
    # 5. Restore standard ReportLab bullet entity if we had it
    text = text.replace("&amp;bull;", "&bull;")
    return text

def add_markdown_flowables(text: str, story: list, body_style, heading_style):
    """
    Parses complex multi-paragraph scientific markdown text, converting
    it into high-fidelity independent ReportLab Paragraph flowables.
    """
    if not text:
        return
        
    import re
    from reportlab.platypus import Paragraph, Spacer
    
    # 1. Clean up excessive decorative separators (e.g. ===, ---, ___ or »»»)
    text = re.sub(r'[=\-_»~—]{3,}', '', text)
    
    # 2. Pre-process dialogue lines to split the dialogue label from the response
    # if followed by markdown headers or lists to prevent nested header glitches.
    text = re.sub(
        r'\*\*(AI Consultant|Researcher):\*\*\s*(##+|-\s*|\*\s*|•\s*)',
        r'**\1:**\n\n\2',
        text
    )
    
    # 3. Split into distinct logical blocks by double newlines
    blocks = text.split("\n\n")
    for block in blocks:
        block_stripped = block.strip()
        if not block_stripped:
            continue
            
        # Parse Setext header: line followed by a divider line of === or ---
        lines = [l.strip() for l in block_stripped.split("\n") if l.strip()]
        if len(lines) == 2 and re.match(r'^[=\-]{3,}$', lines[1]):
            clean_title = parse_inline_markdown(lines[0])
            story.append(Paragraph(clean_title, heading_style))
            continue
            
        # If the block contains inline markdown headers or lists, process line-by-line
        # to ensure that headings/bullets inside a block are parsed independently.
        has_internal_headers_or_lists = False
        for line in lines:
            l_stripped = line.strip()
            if l_stripped.startswith("### ") or l_stripped.startswith("## ") or l_stripped.startswith("# ") or l_stripped.startswith("- ") or l_stripped.startswith("* ") or l_stripped.startswith("• "):
                has_internal_headers_or_lists = True
                break
                
        if has_internal_headers_or_lists:
            for line in block_stripped.split("\n"):
                l_stripped = line.strip()
                if not l_stripped:
                    continue
                    
                if l_stripped.startswith("### "):
                    clean_title = parse_inline_markdown(l_stripped[4:].strip())
                    story.append(Paragraph(clean_title, heading_style))
                elif l_stripped.startswith("## "):
                    clean_title = parse_inline_markdown(l_stripped[3:].strip())
                    story.append(Paragraph(clean_title, heading_style))
                elif l_stripped.startswith("# "):
                    clean_title = parse_inline_markdown(l_stripped[2:].strip())
                    story.append(Paragraph(clean_title, heading_style))
                elif l_stripped.startswith("- ") or l_stripped.startswith("* ") or l_stripped.startswith("• "):
                    content = l_stripped.lstrip("-*• ")
                    content_xml = parse_inline_markdown(content)
                    story.append(Paragraph(f"&bull; {content_xml}", body_style))
                else:
                    content_xml = parse_inline_markdown(l_stripped)
                    story.append(Paragraph(content_xml, body_style))
            continue

        # Handle single block starting with ATX headers
        if block_stripped.startswith("### "):
            clean_title = parse_inline_markdown(block_stripped[4:].strip())
            story.append(Paragraph(clean_title, heading_style))
        elif block_stripped.startswith("## "):
            clean_title = parse_inline_markdown(block_stripped[3:].strip())
            story.append(Paragraph(clean_title, heading_style))
        elif block_stripped.startswith("# "):
            clean_title = parse_inline_markdown(block_stripped[2:].strip())
            story.append(Paragraph(clean_title, heading_style))
            
        # Handle pure Bullet List Blocks
        elif block_stripped.startswith("- ") or block_stripped.startswith("* ") or block_stripped.startswith("• "):
            for line in block_stripped.split("\n"):
                l_stripped = line.strip()
                if l_stripped.startswith("- ") or l_stripped.startswith("* ") or l_stripped.startswith("• "):
                    content = l_stripped.lstrip("-*• ")
                    content_xml = parse_inline_markdown(content)
                    story.append(Paragraph(f"&bull; {content_xml}", body_style))
            
        # Handle standard scientific body text block
        else:
            cleaned_p = " ".join(lines)
            p_xml = parse_inline_markdown(cleaned_p)
            story.append(Paragraph(p_xml, body_style))

def generate_pdf_report(plots_data: Dict[str, str], diagnoses_data: Dict[str, str]) -> io.BytesIO:
    """
    Generates a publication-grade scientific PDF report with embedded charts
    and visual AI diagnostics formatted neatly for researchers.
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError(
            "ReportLab is not installed. Please run command: "
            "../.venv/bin/pip install reportlab"
        )

    pdf_buffer = io.BytesIO()
    temp_files = []
    # Margins are 0.75 in (54 pt). Page width is 612, printable width is 504 pt.
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom scientific document palette matching strict design requirements
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A365D"),
        alignment=1,  # Center alignment
        spaceAfter=12
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=18,
        textColor=colors.HexColor("#4A5568"),
        alignment=1,
        spaceAfter=20
    )

    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=18,
        textColor=colors.HexColor("#1A365D"),
        spaceBefore=14,
        spaceAfter=12
    )

    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=12,
        leading=18,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=12
    )

    story = []

    # Document Header Branding
    story.append(Paragraph("AI Scientific Spectroscopy Diagnostics Report", title_style))
    date_str = datetime.now().strftime("%B %d, %Y - %H:%M")
    story.append(Paragraph(f"AUTOGENERATED SCIENCE PIPELINE REPORT &bull; {date_str}", subtitle_style))
    story.append(Spacer(1, 8))

    def sort_plots_scientifically(plot_name: str):
        # Preprocessing stage weight
        stage_weight = 99
        name_lower = plot_name.lower()
        if name_lower.startswith("raw"):
            stage_weight = 10
        elif name_lower.startswith("snv"):
            stage_weight = 20
        elif name_lower.startswith("savgol"):
            stage_weight = 30
        elif name_lower.startswith("meancentered") or name_lower.startswith("mean_centered"):
            stage_weight = 40
            
        # Chart type weight within the stage
        chart_weight = 99
        if "spectra" in name_lower:
            chart_weight = 1
        elif "scores" in name_lower:
            chart_weight = 2
        elif "scree" in name_lower:
            chart_weight = 3
        elif "loadings" in name_lower:
            chart_weight = 4
        elif "residuals" in name_lower:
            chart_weight = 5
        elif "heatmap" in name_lower:
            chart_weight = 6
            
        return (stage_weight, chart_weight, plot_name)

    # Add each plot page by page
    sorted_plots = sorted(plots_data.keys(), key=sort_plots_scientifically)
    for idx, plot_type in enumerate(sorted_plots):
        base64_str = plots_data[plot_type]
        if not base64_str:
            continue

        if idx > 0:
            story.append(PageBreak())

        # Subtitle for specific plot
        story.append(Paragraph(f"{plot_type} Analysis Overview", section_style))
        story.append(Spacer(1, 6))

        # Decode base64 image and write to a temporary file for 100% reliable local filesystem embedding
        import tempfile
        import os
        temp_filename = None
        try:
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
            img_data = base64.b64decode(base64_str)
            
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_f:
                temp_f.write(img_data)
                temp_filename = temp_f.name
            
            # Embed image from local temp file path
            story.append(Image(temp_filename, width=410, height=250))
            story.append(Spacer(1, 10))
            temp_files.append(temp_filename)
        except Exception as e:
            logger.error(f"Failed to load image for {plot_type}: {e}")
            story.append(Paragraph("<i>[Visual spectroscopy chart failed to embed]</i>", body_style))
            story.append(Spacer(1, 8))

        # Append visual diagnosis
        story.append(Paragraph("<b>AI Scientific Visual Analysis & Insights:</b>", body_style))
        story.append(Spacer(1, 3))
        
        diag_text = diagnoses_data.get(
            plot_type, 
            "No AI diagnostics performed for this plot in the current session."
        )
        add_markdown_flowables(diag_text, story, body_style, section_style)

    try:
        doc.build(story)
    finally:
        # Clean up temporary files immediately
        for path in temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.error(f"Failed to delete temp file {path}: {e}")
                
    pdf_buffer.seek(0)
    return pdf_buffer
