from dataclasses import dataclass

from app.dto.response.base_response import BaseResponse


@dataclass
class PaginateResponse(BaseResponse):
    page: int = None
    limit: int = None
    count: int = None

    def set_metadata(self, page, limit, count):
        self.page = page
        self.limit = limit
        self.count = count
