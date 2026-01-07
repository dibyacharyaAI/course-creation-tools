from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from typing import Optional
from .contracts import SlideStructure

import logging
logger = logging.getLogger(__name__)

class PDFBuilder:
    def __init__(self):
        self.width, self.height = A4
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        # Define custom styles, overriding if necessary
        styles_to_add = [
            ParagraphStyle(name='SlideTitle', parent=self.styles['Heading2'], fontSize=14, spaceAfter=6, textColor=colors.darkblue),
            ParagraphStyle(name='Bullet', parent=self.styles['BodyText'], leftIndent=20, bulletIndent=10, spaceAfter=2),
            ParagraphStyle(name='NotesLabel', parent=self.styles['BodyText'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.grey),
            ParagraphStyle(name='Notes', parent=self.styles['BodyText'], fontSize=10, leftIndent=0, spaceAfter=6),
            ParagraphStyle(name='PromptLabel', parent=self.styles['BodyText'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.purple),
            ParagraphStyle(name='Prompt', parent=self.styles['BodyText'], fontSize=9, fontName='Courier', leftIndent=0, spaceAfter=12)
        ]
        
        for style in styles_to_add:
            try:
                self.styles.add(style)
            except KeyError:
                # Style exists, verify if we can ignore or replace. 
                # For now logging and ignoring to allow build to proceed.
                logger.warning(f"Style {style.name} already exists in stylesheet.")
                pass

    def build(self, slide_plan: SlideStructure, output_path: str):
        """Generates PDF Handout"""
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)
        
        story = []
        
        # Title Page (Optional, for now just start)
        story.append(Paragraph("Course Handout", self.styles['Title']))
        story.append(Spacer(1, 0.5 * inch))
        
        for slide in slide_plan.slides:
            # Group slide content
            elements = []
            
            # Slide Header
            elements.append(Paragraph(f"Slide {slide.id}: {slide.title}", self.styles['SlideTitle']))
            
            # Bullets
            for bullet in slide.bullets:
                elements.append(Paragraph(f"• {bullet}", self.styles['Bullet']))
            elements.append(Spacer(1, 0.1 * inch))
            
            # Illustration
            if slide.illustration_prompt:
                elements.append(Paragraph("Illustration Prompt:", self.styles['PromptLabel']))
                elements.append(Paragraph(slide.illustration_prompt, self.styles['Prompt']))
                
            # Speaker Notes
            if slide.speaker_notes:
                elements.append(Paragraph("Speaker Notes:", self.styles['NotesLabel']))
                elements.append(Paragraph(slide.speaker_notes, self.styles['Notes']))
                
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(Paragraph("_" * 60, self.styles['BodyText'])) # Divider
            elements.append(Spacer(1, 0.2 * inch))

            # Keep slide content together if possible, or just append
            story.append(KeepTogether(elements))
            
        doc.build(story)
        logger.info(f"PDF Generated at {output_path}")
        return output_path
