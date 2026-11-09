"""
Module: Document & File Parser
Extracts readable text from:
- Images (.png, .jpg, .jpeg, .webp, .bmp) via OCR
- Email files (.eml, .msg)
- PDFs (.pdf) via pypdf
- Word documents (.docx) via python-docx
- Text files (.txt, .csv, .log)
"""

import os
import sys
import io
import email
from email import policy
from email.parser import BytesParser
import pypdf
import docx

# Ensure UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


class DocumentParser:
    """
    Parses various file formats into clean text suitable for spam classification.
    """

    SUPPORTED_EXTENSIONS = {
        # Documents
        '.pdf': 'PDF Document',
        '.docx': 'Word Document',
        '.doc': 'Word Document',
        '.eml': 'Email Message (.eml)',
        '.msg': 'Outlook Message (.msg)',
        '.txt': 'Plain Text File',
        '.csv': 'CSV File',
        '.log': 'Log File',
        # Images
        '.png': 'Image (PNG)',
        '.jpg': 'Image (JPEG)',
        '.jpeg': 'Image (JPEG)',
        '.webp': 'Image (WebP)',
        '.bmp': 'Image (Bitmap)'
    }

    @staticmethod
    def is_supported(filename: str) -> bool:
        ext = os.path.splitext(filename.lower())[1]
        return ext in DocumentParser.SUPPORTED_EXTENSIONS

    @staticmethod
    def get_file_type(filename: str) -> str:
        ext = os.path.splitext(filename.lower())[1]
        return DocumentParser.SUPPORTED_EXTENSIONS.get(ext, 'Unknown Document')

    @classmethod
    def parse_file(cls, file_bytes: bytes, filename: str) -> dict:
        """
        Extracts text from raw file bytes.
        Returns dict:
            {
                'filename': str,
                'file_type': str,
                'extracted_text': str,
                'metadata': dict,
                'is_image': bool
            }
        """
        ext = os.path.splitext(filename.lower())[1]
        file_type = cls.get_file_type(filename)
        is_image = ext in ('.png', '.jpg', '.jpeg', '.webp', '.bmp')

        extracted_text = ""
        metadata = {}

        try:
            if ext == '.pdf':
                extracted_text, metadata = cls._parse_pdf(file_bytes)
            elif ext in ('.docx', '.doc'):
                extracted_text, metadata = cls._parse_docx(file_bytes)
            elif ext in ('.eml', '.msg'):
                extracted_text, metadata = cls._parse_eml(file_bytes)
            elif is_image:
                extracted_text, metadata = cls._parse_image(file_bytes, filename)
            else:
                # Text / Fallback
                extracted_text = file_bytes.decode('utf-8', errors='replace').strip()
                metadata = {'char_count': len(extracted_text)}

        except Exception as e:
            extracted_text = f"Error extracting text from {filename}: {str(e)}"
            metadata = {'error': str(e)}

        return {
            'filename': filename,
            'file_type': file_type,
            'extracted_text': extracted_text.strip(),
            'metadata': metadata,
            'is_image': is_image
        }

    @staticmethod
    def _parse_pdf(file_bytes: bytes) -> tuple:
        """Extracts text from PDF bytes using pypdf."""
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages_text = []
        for i, page in enumerate(reader.pages):
            txt = page.extract_text()
            if txt:
                pages_text.append(txt)

        full_text = "\n\n".join(pages_text).strip()
        metadata = {
            'total_pages': len(reader.pages),
            'char_count': len(full_text)
        }
        return full_text, metadata

    @staticmethod
    def _parse_docx(file_bytes: bytes) -> tuple:
        """Extracts text from Word DOCX bytes."""
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        
        # Also extract table text
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)

        full_text = "\n".join(paragraphs).strip()
        metadata = {
            'paragraphs_count': len(paragraphs),
            'char_count': len(full_text)
        }
        return full_text, metadata

    @staticmethod
    def _parse_eml(file_bytes: bytes) -> tuple:
        """Extracts headers and body from RFC 822 email bytes."""
        msg = BytesParser(policy=policy.default).parsebytes(file_bytes)

        subject = msg.get('subject', '') or ''
        sender = msg.get('from', '') or ''
        to = msg.get('to', '') or ''
        date = msg.get('date', '') or ''

        body_parts = []
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdisp = str(part.get("Content-Disposition", ""))
                if ctype == "text/plain" and "attachment" not in cdisp:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_parts.append(payload.decode(errors='replace'))
                    except Exception:
                        pass
                elif ctype == "text/html" and not body_parts and "attachment" not in cdisp:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_parts.append(payload.decode(errors='replace'))
                    except Exception:
                        pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode(errors='replace'))
                else:
                    body_parts.append(str(msg.get_payload()))
            except Exception:
                body_parts.append(str(msg.get_payload()))

        body_text = " ".join(body_parts).strip()
        full_text = f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{body_text}".strip()

        metadata = {
            'subject': subject,
            'sender': sender,
            'recipient': to,
            'date': str(date)
        }
        return full_text, metadata

    @staticmethod
    def _parse_image(file_bytes: bytes, filename: str) -> tuple:
        """
        Attempts OCR on image using pytesseract if available,
        otherwise marks image for client-side Tesseract.js processing.
        """
        extracted_text = ""
        ocr_source = "None"

        # 1. Try pytesseract if installed
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            extracted_text = pytesseract.image_to_string(img).strip()
            if extracted_text:
                ocr_source = "PyTesseract"
        except Exception:
            pass

        metadata = {
            'ocr_engine': ocr_source,
            'image_format': filename.split('.')[-1].upper(),
            'needs_client_ocr': not bool(extracted_text)
        }
        return extracted_text, metadata


if __name__ == "__main__":
    test_txt = b"Congratulations! You won Rs 10 lakh in lottery. Call now to claim."
    res = DocumentParser.parse_file(test_txt, "sample.txt")
    print("Parsed result:", res)
