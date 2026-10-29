"""Validate BibTeX metadata against Crossref records."""
from .core import parse_bibtex, compare, validate, crossref_fetch, title_similarity

__version__ = "0.1.0"
__all__ = ["parse_bibtex", "compare", "validate", "crossref_fetch", "title_similarity"]
