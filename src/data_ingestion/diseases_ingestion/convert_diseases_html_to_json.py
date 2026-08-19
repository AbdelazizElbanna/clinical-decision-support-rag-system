"""
convert_disease_html_to_json.py
───────────────────────────────
Converts raw disease HTML files into structured JSON documents.

This is the first stage of the disease data ingestion pipeline:

    Raw HTML  →  Structured JSON

The script extracts meaningful textual content (headings, paragraphs, lists)
from scraped medical web pages (primarily from the American Academy of
Dermatology) while stripping navigation, scripts, styles, ads, and other
non-content elements.

The resulting JSON preserves source metadata (URL, title, filename) and
structures content as an ordered sequence of typed blocks suitable for
downstream chunking and embedding.

Usage:
    # Convert a single HTML file
    python convert_disease_html_to_json.py --input page.html --output out/

    # Convert all HTML files in a directory
    python convert_disease_html_to_json.py --input data/raw/diseases/Eczema/ --output data/raw/diseases/Eczema/

    # Using project defaults (data/raw/diseases → data/raw/diseases)
    python convert_disease_html_to_json.py

Dependencies:
    - beautifulsoup4 (bs4)
    - lxml  (recommended HTML parser; falls back to html.parser)
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from bs4 import BeautifulSoup, Comment, NavigableString, Tag
except ImportError:
    print(
        "ERROR: beautifulsoup4 is required. Install it with:\n"
        "  pip install beautifulsoup4 lxml",
        file=sys.stderr,
    )
    sys.exit(1)

# ──────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "diseases"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "diseases"

# HTML parser preference (lxml is faster and more forgiving)
try:
    import lxml  # noqa: F401

    HTML_PARSER = "lxml"
except ImportError:
    HTML_PARSER = "html.parser"

# Tags that contain no useful medical content
STRIP_TAGS = {
    "script",
    "style",
    "noscript",
    "iframe",
    "svg",
    "button",
    "input",
    "select",
    "textarea",
    "form",
    "nav",
    "picture",
    "source",
    "video",
    "audio",
    "canvas",
    "map",
    "area",
}

# CSS classes / IDs that mark non-content regions on AAD pages
NON_CONTENT_CLASSES = {
    "header-public",
    "header-desktop",
    "header-mobile",
    "breadcrumbs-bar-container",
    "ad-container",
    "footer",
    "footer-public",
    "account-sidebar",
    "dropdown-container",
    "mobile-nav",
    "sec-nav-container",
    "link-tabs-vert-container",
    "link-tabs-intro",
    "callout",
    "soc-med-share-block",
    "cookie-consent",
}

# Heading tags in priority order
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

# Block-level tags whose text should be treated as paragraphs
BLOCK_TAGS = {"p", "div", "blockquote", "figcaption", "dd", "dt", "td", "th"}


# ──────────────────────────────────────────────────────────────────────
# Text normalization
# ──────────────────────────────────────────────────────────────────────


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to single spaces, strip edges."""
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def clean_text(text: str) -> str:
    """
    Normalize text extracted from HTML while preserving medical content.

    - Collapses whitespace
    - Strips leading/trailing whitespace
    - Does NOT alter medical terminology, dosages, or abbreviations
    """
    if not text:
        return ""
    text = normalize_whitespace(text)
    # Remove stray leading punctuation artifacts from HTML extraction
    text = re.sub(r"^[:\-–—]+\s*", "", text)
    return text.strip()


# ──────────────────────────────────────────────────────────────────────
# Metadata extraction
# ──────────────────────────────────────────────────────────────────────


def extract_metadata(soup: BeautifulSoup, html_path: Path) -> dict[str, Any]:
    """
    Extract page-level metadata from the HTML document.

    Returns a dict with:
        - source_file: filename of the HTML
        - title: page title
        - url: original source URL (from og:url or canonical link)
        - description: meta description
        - extraction_date: ISO timestamp of conversion
    """
    metadata: dict[str, Any] = {
        "source_file": html_path.name,
        "title": None,
        "url": None,
        "description": None,
        "extraction_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    # Title: prefer <title> tag content
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        metadata["title"] = clean_text(title_tag.string)

    # URL: prefer og:url, then canonical link
    og_url = soup.find("meta", property="og:url")
    if og_url and og_url.get("content"):
        metadata["url"] = og_url["content"].strip()
    else:
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            metadata["url"] = canonical["href"].strip()

    # Description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        metadata["description"] = clean_text(meta_desc["content"])
    else:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            metadata["description"] = clean_text(og_desc["content"])

    return metadata


# ──────────────────────────────────────────────────────────────────────
# Content extraction
# ──────────────────────────────────────────────────────────────────────


def _should_skip_element(tag: Tag) -> bool:
    """Check if a tag belongs to a non-content region."""
    if tag.name in STRIP_TAGS:
        return True

    # Check CSS classes
    classes = tag.get("class", [])
    if isinstance(classes, list):
        class_str = " ".join(classes)
    else:
        class_str = str(classes)

    for non_content_class in NON_CONTENT_CLASSES:
        if non_content_class in class_str:
            return True

    # Check if inside a <!--BeginNoIndex--> / <!--EndNoIndex--> block
    # by looking at the tag's parent chain for known non-content markers
    tag_id = tag.get("id", "")
    if isinstance(tag_id, list):
        tag_id = " ".join(tag_id)

    # Skip ad containers by ID pattern
    if tag_id and ("ad-" in tag_id or "sticky-" in tag_id):
        return True

    return False


def _is_in_non_content_region(tag: Tag) -> bool:
    """Walk up the parent chain to see if any ancestor is non-content."""
    current = tag.parent
    while current and isinstance(current, Tag):
        if _should_skip_element(current):
            return True
        current = current.parent
    return False


def _extract_list_items(list_tag: Tag) -> list[str]:
    """Extract text items from a <ul> or <ol> tag."""
    items = []
    for li in list_tag.find_all("li", recursive=False):
        text = clean_text(li.get_text())
        if text:
            items.append(text)
    return items


def extract_main_content(soup: BeautifulSoup) -> Tag | None:
    """
    Locate the main content area of the page.

    For AAD pages, the main content is inside <main class="col-lg-9">.
    Falls back to <main>, <article>, or <section class="content">.
    """
    # AAD-specific: <main class="col-lg-9">
    main = soup.find("main")
    if main:
        return main

    # Fallback: <article>
    article = soup.find("article")
    if article:
        return article

    # Fallback: <section class="content">
    content_section = soup.find("section", class_="content")
    if content_section:
        return content_section

    # Fallback: <div id="content"> or similar
    for attr in ["content", "main-content", "article-content", "page-content"]:
        container = soup.find(id=attr)
        if container:
            return container
        container = soup.find(class_=attr)
        if container:
            return container

    # Last resort: entire <body>
    return soup.find("body")


def extract_content_blocks(container: Tag) -> list[dict[str, Any]]:
    """
    Walk the content container and extract an ordered sequence of
    content blocks (headings, paragraphs, lists).

    Each block is a dict with:
        - type: "heading" | "paragraph" | "list"
        - text: (for heading/paragraph) the text content
        - level: (for heading only) the heading level (1-6)
        - items: (for list only) list of text items
        - list_type: (for list only) "ordered" | "unordered"

    Medical text is preserved faithfully. Only truly empty blocks
    are filtered out.
    """
    blocks: list[dict[str, Any]] = []
    seen_texts: set[str] = set()  # Deduplicate exact-repeat blocks

    def _process_element(element: Tag) -> None:
        """Process a single element and its children."""
        if not isinstance(element, Tag):
            return

        if _should_skip_element(element):
            return

        tag_name = element.name

        # ── Headings ──
        if tag_name in HEADING_TAGS:
            text = clean_text(element.get_text())
            if text and text not in seen_texts:
                level = int(tag_name[1])
                blocks.append({
                    "type": "heading",
                    "level": level,
                    "text": text,
                })
                seen_texts.add(text)
            return  # Don't recurse into headings

        # ── Lists ──
        if tag_name in ("ul", "ol"):
            items = _extract_list_items(element)
            if items:
                list_type = "ordered" if tag_name == "ol" else "unordered"
                # Create a fingerprint for dedup
                fingerprint = "|".join(items)
                if fingerprint not in seen_texts:
                    blocks.append({
                        "type": "list",
                        "list_type": list_type,
                        "items": items,
                    })
                    seen_texts.add(fingerprint)
            return  # Don't recurse into list children

        # ── Paragraphs and block-level text ──
        if tag_name in BLOCK_TAGS:
            # Check if this element directly contains text
            # (not just wrapper divs with child blocks)
            has_direct_text = False
            has_block_children = False

            for child in element.children:
                if isinstance(child, NavigableString) and clean_text(str(child)):
                    has_direct_text = True
                elif isinstance(child, Tag):
                    if child.name in HEADING_TAGS | {"ul", "ol"} | BLOCK_TAGS:
                        has_block_children = True
                    elif child.name in ("a", "strong", "em", "b", "i", "span",
                                        "br", "sub", "sup", "mark", "abbr",
                                        "small", "u", "s", "code"):
                        # Inline elements contribute text
                        if clean_text(child.get_text()):
                            has_direct_text = True

            if has_direct_text and not has_block_children:
                text = clean_text(element.get_text())
                if text and text not in seen_texts:
                    blocks.append({
                        "type": "paragraph",
                        "text": text,
                    })
                    seen_texts.add(text)
                return  # Already captured the text

            if has_block_children:
                # Recurse into children, but also capture any direct text
                # that precedes or follows the block children
                for child in element.children:
                    if isinstance(child, Tag):
                        _process_element(child)
                return

            # No block children and no direct text — still try to extract
            text = clean_text(element.get_text())
            if text and text not in seen_texts:
                blocks.append({
                    "type": "paragraph",
                    "text": text,
                })
                seen_texts.add(text)
            return

        # ── Image blocks with descriptive alt/caption text ──
        if tag_name == "img":
            alt_text = element.get("alt", "")
            if alt_text:
                alt_text = clean_text(alt_text)
                # Only keep substantive alt text (not just branding)
                if (alt_text
                        and len(alt_text) > 20
                        and "American Academy of Dermatology" not in alt_text
                        and alt_text not in seen_texts):
                    blocks.append({
                        "type": "paragraph",
                        "text": f"[Image: {alt_text}]",
                    })
                    seen_texts.add(alt_text)
            return

        # ── Sections and other containers: recurse ──
        if tag_name in ("section", "main", "article", "aside",
                         "figure", "details", "summary", "table",
                         "thead", "tbody", "tfoot", "tr"):
            if tag_name == "aside":
                # Skip sidebar content (callouts, sponsorship notices, nav)
                return
            for child in element.children:
                if isinstance(child, Tag):
                    _process_element(child)
            return

        # ── Horizontal rules as section breaks ──
        if tag_name == "hr":
            return  # Ignore, section breaks are implied by headings

        # ── Generic containers: recurse into children ──
        for child in element.children:
            if isinstance(child, Tag):
                _process_element(child)

    # Start processing from the container's children
    for child in container.children:
        if isinstance(child, Tag):
            _process_element(child)

    return blocks


# ──────────────────────────────────────────────────────────────────────
# HTML → JSON conversion
# ──────────────────────────────────────────────────────────────────────


def convert_html_to_json(html_path: Path) -> dict[str, Any]:
    """
    Convert a single disease HTML file to a structured JSON document.

    Returns a dict with:
        - source_file: original HTML filename
        - title: page title
        - url: source URL
        - description: meta description
        - extraction_date: ISO conversion timestamp
        - content: ordered list of content blocks
    """
    logger.info("Processing: %s", html_path.name)

    # Read HTML
    try:
        html_text = html_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        html_text = html_path.read_text(encoding="latin-1")
        logger.warning(
            "File %s was not UTF-8; decoded as latin-1", html_path.name
        )

    if not html_text.strip():
        logger.warning("Empty HTML file: %s", html_path.name)
        return {
            "source_file": html_path.name,
            "title": None,
            "url": None,
            "description": None,
            "extraction_date": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "content": [],
        }

    # Parse HTML
    soup = BeautifulSoup(html_text, HTML_PARSER)

    # Remove HTML comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # Remove script/style tags entirely
    for tag_name in ("script", "style", "noscript"):
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Extract metadata
    metadata = extract_metadata(soup, html_path)

    # Find the main content container
    content_container = extract_main_content(soup)
    if content_container is None:
        logger.warning(
            "Could not locate main content area in %s; "
            "extracting from full document",
            html_path.name,
        )
        content_container = soup.find("body") or soup

    # Extract content blocks
    content_blocks = extract_content_blocks(content_container)

    # Filter out blocks that are clearly not medical content
    filtered_blocks = _filter_non_medical_blocks(content_blocks)

    logger.info(
        "  Extracted %d content blocks (%d headings, %d paragraphs, %d lists)",
        len(filtered_blocks),
        sum(1 for b in filtered_blocks if b["type"] == "heading"),
        sum(1 for b in filtered_blocks if b["type"] == "paragraph"),
        sum(1 for b in filtered_blocks if b["type"] == "list"),
    )

    # Build JSON document
    document = {
        "source_file": metadata["source_file"],
        "title": metadata["title"],
        "url": metadata["url"],
        "description": metadata["description"],
        "extraction_date": metadata["extraction_date"],
        "content": filtered_blocks,
    }

    return document


def _filter_non_medical_blocks(
    blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Post-extraction filter to remove blocks that are clearly
    non-medical content (navigation labels, ad markers, etc.)
    while being conservative to avoid removing medical text.
    """
    # Short strings that are almost certainly navigation or UI elements
    nav_labels = {
        "advertisement",
        "sign in",
        "sign-in",
        "log out",
        "go",
        "search",
        "donate",
        "main menu",
        "back",
        "welcome!",
        "for aad members",
    }

    filtered = []
    for block in blocks:
        if block["type"] in ("heading", "paragraph"):
            text = block["text"]
            text_lower = text.lower().strip()

            # Skip very short navigation-like text
            if text_lower in nav_labels:
                continue

            # Skip text that is only "Advertisement" or similar
            if text_lower.startswith("advertisement"):
                continue

            # Skip image credit lines (but NOT clinical image descriptions)
            # Keep "Image:" blocks since they contain clinical descriptions
            if text_lower.startswith("image ") and ":" not in text_lower:
                # Likely "Image 1: Getty Images" — keep it as provenance
                pass

        filtered.append(block)

    return filtered


# ──────────────────────────────────────────────────────────────────────
# Batch processing
# ──────────────────────────────────────────────────────────────────────


def find_html_files(input_path: Path) -> list[Path]:
    """
    Find HTML files at the given path.

    If input_path is a file, return it as a single-item list.
    If input_path is a directory, find all .html files recursively.
    """
    if input_path.is_file():
        if input_path.suffix.lower() in (".html", ".htm"):
            return [input_path]
        else:
            logger.error("Input file is not an HTML file: %s", input_path)
            return []

    if input_path.is_dir():
        html_files = []
        for html_file in sorted(input_path.rglob("*.html")):
            html_files.append(html_file)

        # Also check for .htm extension
        for htm_file in sorted(input_path.rglob("*.htm")):
            if htm_file not in html_files:
                html_files.append(htm_file)

        return sorted(html_files)

    logger.error("Input path does not exist: %s", input_path)
    return []


def resolve_output_path(
    html_path: Path,
    input_base: Path,
    output_base: Path,
) -> Path:
    """
    Determine the output JSON path for a given HTML file.

    Preserves the relative directory structure from input_base,
    replaces the .html extension with .json.
    """
    try:
        relative = html_path.relative_to(input_base)
    except ValueError:
        # html_path is not under input_base; use just the filename
        relative = Path(html_path.name)

    json_name = relative.with_suffix(".json")
    return output_base / json_name


def process_batch(
    input_path: Path,
    output_path: Path,
) -> tuple[int, int]:
    """
    Process one or more HTML files and write JSON output.

    Returns (success_count, error_count).
    """
    html_files = find_html_files(input_path)

    if not html_files:
        logger.error("No HTML files found at: %s", input_path)
        return 0, 0

    logger.info("Found %d HTML file(s) to process", len(html_files))

    # Determine the base for relative path computation
    if input_path.is_file():
        input_base = input_path.parent
    else:
        input_base = input_path

    success_count = 0
    error_count = 0

    for html_file in html_files:
        try:
            # Convert HTML → JSON dict
            document = convert_html_to_json(html_file)

            # Determine output file path
            json_path = resolve_output_path(html_file, input_base, output_path)

            # Create output directory if needed
            json_path.parent.mkdir(parents=True, exist_ok=True)

            # Write JSON
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(document, f, ensure_ascii=False, indent=2)

            size_kb = json_path.stat().st_size / 1024
            logger.info("  → Wrote: %s (%.1f KB)", json_path.name, size_kb)
            success_count += 1

        except Exception as exc:
            logger.error(
                "Failed to process %s: %s", html_file.name, exc, exc_info=True
            )
            error_count += 1

    return success_count, error_count


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert disease HTML files into structured JSON documents. "
            "Extracts headings, paragraphs, and lists from scraped medical "
            "web pages while preserving source metadata."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --input page.html --output output/\n"
            "  %(prog)s --input data/raw/diseases/ --output data/raw/diseases/\n"
            "  %(prog)s   (uses project defaults)\n"
        ),
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help=(
            "Path to a single HTML file or a directory containing HTML files. "
            f"Default: {DEFAULT_INPUT.relative_to(PROJECT_ROOT)}"
        ),
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=(
            "Directory to write JSON output files. "
            f"Default: {DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)}"
        ),
    )

    args = parser.parse_args()
    input_path: Path = args.input
    output_path: Path = args.output

    # Validate input
    if not input_path.exists():
        logger.error("Input path does not exist: %s", input_path)
        sys.exit(1)

    logger.info("Input:  %s", input_path)
    logger.info("Output: %s", output_path)
    logger.info("Parser: %s", HTML_PARSER)

    # Process
    success, errors = process_batch(input_path, output_path)

    # Summary
    logger.info("─" * 56)
    logger.info("  Conversion complete")
    logger.info("  Successful: %d", success)
    if errors:
        logger.error("  Errors: %d", errors)
    logger.info("─" * 56)

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
