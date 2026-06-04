
"""
鏂囨。瑙ｆ瀽妯″潡
浣跨敤unstructured搴撹В鏋愬绫婚潪缁撴瀯鍖栨枃妗?
鏀寔PDF銆乄ord銆丠TML銆乀XT绛夋牸寮?
鏀寔OCR璇嗗埆锛堥渶瑕佸畨瑁呯浉鍏充緷璧栵級
"""
import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.partition.docx import partition_docx
    from unstructured.partition.text import partition_text
    from unstructured.partition.html import partition_html
    from unstructured.documents.elements import Element, Title, NarrativeText, Table, ListItem
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    logging.getLogger(__name__).warning("unstructured not installed, using fallback (PyPDF2/python-docx)")
    UNSTRUCTURED_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


class DocumentParser:
    """鏂囨。瑙ｆ瀽鍣?- 鏀寔缁撴瀯鍖栬В鏋愪笌鍏冩暟鎹彁鍙?""

    def __init__(self, use_unstructured: bool = False):
        self.use_unstructured = use_unstructured and UNSTRUCTURED_AVAILABLE

    def parse_document(
        self,
        file_path: str,
        original_filename: str,
        file_size: int
    ) -> List[Dict[str, Any]]:
        """
        瑙ｆ瀽鏂囨。锛岃繑鍥炴爣鍑嗗寲缁撴瀯鍖栨暟鎹?
        鏍煎紡: [ { "element_type": "title", "text": "...", "metadata": {...} }, ... ]
        """
        file_ext = os.path.splitext(original_filename)[1].lower()

        elements = []
        base_metadata = {
            "source_file": original_filename,
            "file_type": file_ext.lstrip('.'),
            "file_size": file_size,
            "parse_date": datetime.now().isoformat()
        }

        if self.use_unstructured:
            try:
                elements = self._parse_with_unstructured(file_path, file_ext, base_metadata)
            except Exception as e:
                logging.getLogger(__name__).warning("Unstructured parse failed, using fallback")
                elements = self._parse_fallback(file_path, file_ext, base_metadata)
        else:
            elements = self._parse_fallback(file_path, file_ext, base_metadata)

        return elements

    def _parse_with_unstructured(
        self,
        file_path: str,
        file_ext: str,
        base_metadata: Dict
    ) -> List[Dict[str, Any]]:
        """浣跨敤unstructured瑙ｆ瀽锛堝寮虹増锛?""
        elements = []

        if file_ext == '.pdf':
            elements = partition_pdf(filename=file_path, strategy="auto")
        elif file_ext == '.docx':
            elements = partition_docx(filename=file_path)
        elif file_ext == '.txt':
            elements = partition_text(filename=file_path)
        elif file_ext in ['.html', '.htm']:
            elements = partition_html(filename=file_path)
        else:
            raise ValueError(f"Unsupported format: {file_ext}")

        result = []
        page_num = 1

        for elem in elements:
            elem_type = self._get_element_type(elem)
            metadata = base_metadata.copy()
            metadata["page_number"] = page_num
            if hasattr(elem, 'metadata'):
                metadata.update(elem.metadata.to_dict())

            result.append({
                "element_id": str(uuid.uuid4()),
                "element_type": elem_type,
                "text": elem.text.strip(),
                "metadata": metadata
            })

            if elem_type == "page_break":
                page_num += 1

        return result

    def _parse_fallback(
        self,
        file_path: str,
        file_ext: str,
        base_metadata: Dict
    ) -> List[Dict[str, Any]]:
        """fallback瑙ｆ瀽鏂规硶锛堝吋瀹圭幇鏈変唬鐮侊級"""
        result = []

        if file_ext == '.pdf':
            result = self._parse_pdf_fallback(file_path, base_metadata)
        elif file_ext == '.docx':
            result = self._parse_docx_fallback(file_path, base_metadata)
        elif file_ext in ['.txt', '.md', '.markdown']:
            result = self._parse_txt_fallback(file_path, base_metadata)
        elif file_ext in ['.html', '.htm']:
            result = self._parse_html_fallback(file_path, base_metadata)

        return result

    def _parse_pdf_fallback(
        self,
        file_path: str,
        base_metadata: Dict
    ) -> List[Dict[str, Any]]:
        result = []
        if PdfReader is None:
            raise ImportError("PyPDF2 is required for fallback PDF parsing")
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text:
                    metadata = base_metadata.copy()
                    metadata["page_number"] = page_num
                    result.append({
                        "element_id": str(uuid.uuid4()),
                        "element_type": "narrative_text",
                        "text": text.strip(),
                        "metadata": metadata
                    })
        return result

    def _parse_docx_fallback(
        self,
        file_path: str,
        base_metadata: Dict
    ) -> List[Dict[str, Any]]:
        result = []
        if Document is None:
            raise ImportError("python-docx is required for fallback DOCX parsing")
        doc = Document(file_path)
        para_num = 1
        for para in doc.paragraphs:
            if para.text.strip():
                metadata = base_metadata.copy()
                metadata["paragraph_number"] = para_num
                result.append({
                    "element_id": str(uuid.uuid4()),
                    "element_type": "narrative_text",
                    "text": para.text.strip(),
                    "metadata": metadata
                })
                para_num += 1
        return result

    def _parse_txt_fallback(
        self,
        file_path: str,
        base_metadata: Dict
    ) -> List[Dict[str, Any]]:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        paragraphs = text.split('\n\n')
        result = []
        for idx, para in enumerate(paragraphs):
            if para.strip():
                metadata = base_metadata.copy()
                metadata["paragraph_number"] = idx + 1
                result.append({
                    "element_id": str(uuid.uuid4()),
                    "element_type": "narrative_text",
                    "text": para.strip(),
                    "metadata": metadata
                })
        return result

    def _parse_html_fallback(
        self,
        file_path: str,
        base_metadata: Dict
    ) -> List[Dict[str, Any]]:
        try:
            from bs4 import BeautifulSoup
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            result = []
            text_content = soup.get_text(separator='\n\n')
            paragraphs = text_content.split('\n\n')
            for idx, para in enumerate(paragraphs):
                if para.strip():
                    metadata = base_metadata.copy()
                    metadata["paragraph_number"] = idx + 1
                    result.append({
                        "element_id": str(uuid.uuid4()),
                        "element_type": "narrative_text",
                        "text": para.strip(),
                        "metadata": metadata
                    })
            return result
        except ImportError:
            return self._parse_txt_fallback(file_path, base_metadata)

    def _get_element_type(self, elem: Any) -> str:
        """鑾峰彇鍏冪礌绫诲瀷"""
        if isinstance(elem, Title):
            return "title"
        elif isinstance(elem, Table):
            return "table"
        elif isinstance(elem, ListItem):
            return "list_item"
        elif isinstance(elem, NarrativeText):
            return "narrative_text"
        else:
            return "unknown"


document_parser = DocumentParser(use_unstructured=True)

__all__ = ["DocumentParser", "document_parser"]
