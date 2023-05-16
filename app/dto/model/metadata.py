from dataclasses import dataclass


@dataclass
class Metadata:
    page: int = None
    limit: int = None
    total_elements: int = None
    total_pages: int = None
