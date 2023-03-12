from dataclasses import dataclass

from app.dto.response.base_response import BaseResponse


@dataclass
class PaginateResponse(BaseResponse):
    page: int = None
    limit: int = None
    total_elements: int = None
    total_pages: int = None

    def set_metadata(self, page, limit, total_elements, total_pages):
        self.page = page
        self.limit = limit
        self.total_elements = total_elements
        self.total_pages = total_pages
