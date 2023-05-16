from http import HTTPStatus


# Custom exception class to be used across the application.
class ApplicationException(Exception):
    """
    A custom exception class that can be raised when there is an application-specific error.

    Attributes:
    message (str): A human-readable error message that describes the error.
    status (HTTPStatus): An HTTP status code that corresponds to the error. Defaults to HTTPStatus.BAD_REQUEST (400).
    """

    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status = status
