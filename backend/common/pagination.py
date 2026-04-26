from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Pagination default.

    Query params:
        ?page=1&page_size=50  (max 200)
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
