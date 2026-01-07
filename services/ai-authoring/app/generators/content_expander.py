import os
import json
import logging
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

logger = logging.getLogger(__name__)

class ContentExpander:
    def __init__(self):
        # Patch for local execution
        base_dir = "/app/data" if os.path.exists("/app/data") else "data"
        self.output_dir = f"{base_dir}/generated/content"
        os.makedirs(self.output_dir, exist_ok=True)

    def expand_content(self, slide_plan: dict, course_id: int) -> dict:
        """
        Generates full text content and PDF from the slide plan.
        """
        if not slide_plan or "slides" not in slide_plan:
            logger.error("Invalid slide plan provided for expansion")
            return {}

        # 1. Generate TXT
        lines = []
        lines.append(f"Course Content: {course_id}")
        lines.append("="*40 + "\n")

        for i, slide in enumerate(slide_plan.get("slides", [])):
            lines.append(f"Slide {i+1}: {slide.get('title', 'Untitled')}")
            lines.append("-" * 20)
            
            # Content
            content_items = slide.get('content', [])
            if isinstance(content_items, list):
                for item in content_items:
                    lines.append(f"* {item}")
            elif isinstance(content_items, str):
                lines.append(content_items)
            
            lines.append("\nSpeaker Notes:")
            notes = slide.get('speaker_notes', '')
            lines.append(notes if notes else "(No notes generated)")
            lines.append("\n" + "="*40 + "\n")

        full_text = "\n".join(lines)
        filename_txt = f"course_{course_id}_full.txt"
        path_txt = os.path.join(self.output_dir, filename_txt)
        
        with open(path_txt, "w") as f:
            f.write(full_text)
        logger.info(f"Saved TXT: {path_txt}")

        # 2. Generate PDF
        filename_pdf = f"course_{course_id}_full.pdf"
        path_pdf = os.path.join(self.output_dir, filename_pdf)
        self._generate_pdf(slide_plan, path_pdf, course_id)
        
        return {"txt": path_txt, "pdf": path_pdf, "pptx": None}

    def _generate_pdf(self, slide_plan, output_path, course_id):
        try:
            doc = SimpleDocTemplate(output_path, pagesize=letter,
                                    rightMargin=72, leftMargin=72,
                                    topMargin=72, bottomMargin=18)
            Story = []
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))

            # Title
            title = f"Course Content Bundle: {course_id}"
            Story.append(Paragraph(title, styles["Title"]))
            Story.append(Spacer(1, 12))

            for i, slide in enumerate(slide_plan.get("slides", [])):
                # Slide Title
                slide_title = f"Slide {i+1}: {slide.get('title', 'Untitled')}"
                Story.append(Paragraph(slide_title, styles["Heading2"]))
                
                # Bullets
                content_items = slide.get('content', [])
                bullet_list = []
                if isinstance(content_items, list):
                    for item in content_items:
                        bullet_list.append(ListItem(Paragraph(str(item), styles["Normal"])))
                elif isinstance(content_items, str):
                     bullet_list.append(ListItem(Paragraph(content_items, styles["Normal"])))
                
                if bullet_list:
                    Story.append(ListFlowable(bullet_list, bulletType='bullet', start='circle'))
                
                Story.append(Spacer(1, 12))
                
                # Speaker Notes
                Story.append(Paragraph("<b>Speaker Notes:</b>", styles["Normal"]))
                notes = slide.get('speaker_notes', '(No notes provided)')
                Story.append(Paragraph(str(notes), styles["Justify"]))
                Story.append(Spacer(1, 24))

            doc.build(Story)
            logger.info(f"Saved PDF: {output_path}")
        except Exception as e:
            logger.error(f"PDF Generation Failed: {e}")
            # Do not raise, allow TXT to succeed
