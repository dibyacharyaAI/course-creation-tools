import os
import markdown
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
import logging

logger = logging.getLogger(__name__)

class PDFGenerator:
    def __init__(self, templates_dir: str = "/app/templates", output_dir: str = "/app/exports"):
        self.env = Environment(loader=FileSystemLoader(templates_dir))
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_student_notes(self, course_data: dict) -> str:
        """
        Generate PDF student notes from course data.
        Returns the filename of the generated PDF.
        """
        try:
            template = self.env.get_template("student_notes.html")
            
            # Process markdown in lesson bodies
            modules = course_data.get('content', {}).get('modules', [])
            for module in modules:
                for lesson in module.get('lessons', []):
                    if 'body' in lesson:
                        lesson['body_html'] = markdown.markdown(lesson['body'])
            
            html_content = template.render(
                course=course_data,
                modules=modules,
                metadata=course_data.get('obe_metadata', {})
            )
            
            filename = f"course_{course_data['id']}_notes.pdf"
            output_path = os.path.join(self.output_dir, filename)
            
            HTML(string=html_content).write_pdf(output_path)
            logger.info(f"Generated PDF: {output_path}")
            
            return filename
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise e
