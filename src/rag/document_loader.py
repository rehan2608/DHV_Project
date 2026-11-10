"""
Document loader module for the NIRF RAG system.
Ingests approved documentation across Markdown, Excel, CSV, PDF, and plain text formats,
extracting structural sections, page numbers, and authoritative metadata.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from src.config import PROJECT_ROOT, APPROVED_DOCUMENTS_PATH
from src.rag.exceptions import DocumentLoadingError
from src.rag.text_cleaner import clean_text, clean_markdown_section_title


@dataclass
class DocumentSection:
    """
    Represents a discrete structural section of a loaded document.
    """
    title: Optional[str]
    content: str
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadedDocument:
    """
    Represents a fully loaded and parsed approved document.
    """
    document_id: str
    title: str
    document_type: str
    file_path: str
    format: str
    source_reference: Optional[str]
    description: str
    sections: List[DocumentSection]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Returns the concatenated content of all sections."""
        return "\n\n".join([s.content for s in self.sections if s.content])


class DocumentLoader:
    """
    Loads approved documents into standardized LoadedDocument instances.
    Enforces approved registry validation and extracts section/page context.
    """

    def __init__(
        self,
        approved_documents_path: Optional[Path] = None,
        project_root: Optional[Path] = None,
    ):
        self.project_root = project_root or PROJECT_ROOT
        self.approved_documents_path = approved_documents_path or APPROVED_DOCUMENTS_PATH
        self._registry: List[Dict[str, Any]] = []
        self._load_registry()

    def _load_registry(self) -> None:
        """Loads and validates the approved documents JSON manifest."""
        if not self.approved_documents_path.exists():
            raise DocumentLoadingError(
                f"Approved documents manifest not found at: {self.approved_documents_path}"
            )
        try:
            with open(self.approved_documents_path, "r", encoding="utf-8") as f:
                self._registry = json.load(f)
        except Exception as e:
            raise DocumentLoadingError(f"Failed to parse approved documents manifest: {e}")

    def get_approved_documents_catalog(self) -> List[Dict[str, Any]]:
        """Returns the list of approved document metadata records."""
        return list(self._registry)

    def load_all_approved_documents(self) -> List[LoadedDocument]:
        """
        Loads all approved documents defined in the catalog.
        """
        documents: List[LoadedDocument] = []
        for entry in self._registry:
            if entry.get("approved", False):
                doc = self.load_document(entry)
                documents.append(doc)
        return documents

    def load_document_by_id(self, document_id: str) -> LoadedDocument:
        """
        Loads a single document by its unique document_id from the registry.
        """
        for entry in self._registry:
            if entry.get("document_id") == document_id:
                return self.load_document(entry)
        raise DocumentLoadingError(f"Document ID '{document_id}' is not in the approved documents registry.")

    def load_document(self, entry: Dict[str, Any]) -> LoadedDocument:
        """
        Loads and parses a single document based on its entry descriptor.
        """
        doc_id = entry["document_id"]
        rel_path = entry["file_path"]
        abs_path = self.project_root / rel_path

        if not abs_path.exists():
            # Check fallback in case data directory moved
            alt_path = self.project_root / rel_path.replace("data/NIRF_Final_Cleaned_Dataset/", "NIRF_Final_Cleaned_Dataset/")
            if alt_path.exists():
                abs_path = alt_path
            else:
                raise DocumentLoadingError(f"Approved document file does not exist: {abs_path}")

        fmt = entry.get("format", abs_path.suffix.lstrip(".").lower()).lower()
        title = entry.get("title", abs_path.stem)
        doc_type = entry.get("document_type", "general")
        source_ref = entry.get("source_reference")
        desc = entry.get("description", "")

        try:
            if fmt == "md" or abs_path.suffix == ".md":
                sections = self._load_markdown(abs_path)
            elif fmt in ("xlsx", "xls") or abs_path.suffix in (".xlsx", ".xls"):
                sections = self._load_excel(abs_path, doc_id)
            elif fmt == "csv" or abs_path.suffix == ".csv":
                sections = self._load_csv(abs_path, doc_id)
            elif fmt == "pdf" or abs_path.suffix == ".pdf":
                sections = self._load_pdf(abs_path)
            else:
                sections = self._load_text(abs_path)

            return LoadedDocument(
                document_id=doc_id,
                title=title,
                document_type=doc_type,
                file_path=rel_path,
                format=fmt,
                source_reference=source_ref,
                description=desc,
                sections=sections,
                metadata={"file_size_bytes": abs_path.stat().st_size},
            )
        except Exception as e:
            if isinstance(e, DocumentLoadingError):
                raise
            raise DocumentLoadingError(f"Error loading document '{doc_id}' from {abs_path}: {e}")

    def _load_markdown(self, path: Path) -> List[DocumentSection]:
        """
        Parses Markdown text into sections based on headings (#, ##, ###).
        """
        text = path.read_text(encoding="utf-8")
        text = clean_text(text)

        lines = text.split("\n")
        sections: List[DocumentSection] = []
        current_title: Optional[str] = "Overview"
        current_lines: List[str] = []

        for line in lines:
            if line.startswith("#"):
                # Flush previous section if it has content
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append(DocumentSection(title=current_title, content=content))
                current_title = clean_markdown_section_title(line)
                current_lines = [line]
            else:
                current_lines.append(line)

        # Flush final section
        content = "\n".join(current_lines).strip()
        if content:
            sections.append(DocumentSection(title=current_title, content=content))

        return sections

    def _load_excel(self, path: Path, doc_id: str) -> List[DocumentSection]:
        """
        Parses an Excel spreadsheet into descriptive structural sections.
        Specialized for data_dictionary.xlsx.
        """
        sections: List[DocumentSection] = []
        xl = pd.ExcelFile(path)

        for sheet_name in xl.sheet_names:
            df = xl.parse(sheet_name)
            
            # Detect header row (handle NIRF data dictionary layout where header is row 1)
            if "Field Name" not in df.columns:
                # Check row 1
                row_vals = df.iloc[1].fillna("").astype(str).tolist() if len(df) > 1 else []
                if "Field Name" in row_vals:
                    df = xl.parse(sheet_name, skiprows=2)

            if "Field Name" in df.columns:
                # Add an overview section summarizing the 40 fields
                field_list = [f"- **{r.get('Field Name', '')}** ({r.get('Tableau Alias', '')}): {r.get('Role', '')} - {r.get('Description & Analytical Meaning', '')}" for _, r in df.iterrows() if str(r.get('Field Name', '')).strip() and str(r.get('Field Name', '')).lower() != 'nan']
                overview_content = (
                    "# NIRF Data Dictionary: Complete Schema Overview (40 Columns)\n\n"
                    + "\n".join(field_list)
                )
                sections.append(
                    DocumentSection(
                        title="Data Dictionary: Complete Schema Overview",
                        content=clean_text(overview_content),
                        metadata={"sheet_name": sheet_name, "total_fields": len(field_list)},
                    )
                )

                # Create dedicated, high-resolution sections for each field
                for _, row in df.iterrows():
                    fname = str(row.get("Field Name", "")).strip()
                    if not fname or fname.lower() == "nan":
                        continue
                    alias = str(row.get("Tableau Alias", "")).strip()
                    dtype = str(row.get("Data Type", "")).strip()
                    role = str(row.get("Role", "General")).strip()
                    desc = str(row.get("Description & Analytical Meaning", "")).strip()
                    vrange = str(row.get("Valid Range / Format", "")).strip()
                    missing = str(row.get("Missing Value Interpretation", "")).strip()

                    entry_text = (
                        f"# NIRF Data Dictionary: {fname} ({alias})\n\n"
                        f"Field Name: {fname}\n"
                        f"Tableau Alias: {alias}\n"
                        f"Data Type: {dtype}\n"
                        f"Role: {role}\n"
                        f"Description & Analytical Meaning: {desc}\n"
                        f"Valid Range / Format: {vrange}\n"
                        f"Missing Value Interpretation: {missing}"
                    )
                    sections.append(
                        DocumentSection(
                            title=f"Field: {fname} ({alias})",
                            content=clean_text(entry_text),
                            metadata={"sheet_name": sheet_name, "field_name": fname, "role": role, "alias": alias},
                        )
                    )
            else:
                # Generic tabular sheet conversion
                csv_repr = df.to_string(index=False)
                sections.append(
                    DocumentSection(
                        title=f"Sheet: {sheet_name}",
                        content=clean_text(csv_repr),
                        metadata={"sheet_name": sheet_name},
                    )
                )

        return sections

    def _load_csv(self, path: Path, doc_id: str) -> List[DocumentSection]:
        """
        Parses a CSV file into descriptive sections.
        Specialized for comparability_rules.csv grouping by category.
        """
        df = pd.read_csv(path)
        sections: List[DocumentSection] = []

        if "category" in df.columns and "year" in df.columns:
            # Group by category to capture cross-year comparability rules together
            for category, group in df.groupby("category"):
                rows_text = []
                for _, row in group.sort_values("year").iterrows():
                    rows_text.append(
                        f"Year: {row['year']} | Cohort: {row.get('rank_cohort', 'N/A')} | "
                        f"Metric Schema: {row.get('metric_schema', 'N/A')} | "
                        f"Records: {row.get('published_record_count', 'N/A')} | "
                        f"Max Rank: {row.get('maximum_published_rank', 'N/A')} | "
                        f"Score Available: {row.get('score_available', 'N/A')} | "
                        f"Parameter Scores Available: {row.get('parameter_scores_available', 'N/A')} | "
                        f"Status: {row.get('comparability_status', 'N/A')} | "
                        f"Start Year: {row.get('valid_comparison_start_year', 'N/A')}\n"
                        f"Notes: {row.get('comparability_notes', 'N/A')}"
                    )
                section_content = (
                    f"# Comparability Rules: {category} (2017–2025)\n\n"
                    + "\n\n".join(rows_text)
                )
                sections.append(
                    DocumentSection(
                        title=f"Comparability Rules: {category}",
                        content=clean_text(section_content),
                        metadata={"category": category},
                    )
                )
        else:
            # Generic CSV
            sections.append(
                DocumentSection(
                    title=f"Dataset Table: {path.stem}",
                    content=clean_text(df.to_string(index=False)),
                )
            )

        return sections

    def _load_pdf(self, path: Path) -> List[DocumentSection]:
        """
        Parses a PDF file into page-by-page DocumentSection objects using pypdf.
        """
        import pypdf
        sections: List[DocumentSection] = []
        reader = pypdf.PdfReader(str(abs(path)))
        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            page_text = clean_text(page_text)
            if page_text.strip():
                sections.append(
                    DocumentSection(
                        title=f"Page {idx + 1}",
                        content=page_text,
                        page_number=idx + 1,
                        metadata={"page": idx + 1, "total_pages": len(reader.pages)},
                    )
                )
        return sections

    def _load_text(self, path: Path) -> List[DocumentSection]:
        """
        Parses a plain text file.
        """
        text = path.read_text(encoding="utf-8")
        text = clean_text(text)
        return [DocumentSection(title="Full Document", content=text)]
