from app.services.booker import BookingService
from app.utils.exceptions import (
    ActionNotAvailableError,
    ClassNotFoundError,
    ConfirmationError,
    LoginError,
    NavigationError,
)


class FakePage:
    def __init__(self, text: str = ""):
        self._text = text

    def inner_text(self, _selector: str) -> str:
        return self._text


def test_reason_is_full_on_waitlist_message():
    service = BookingService()
    page = FakePage("Ja està apuntat a la llista d'espera.")
    assert service._reason_for(page, ConfirmationError("x")) == "full"


def test_reason_maps_exception_types():
    service = BookingService()
    page = FakePage("")
    assert service._reason_for(page, ClassNotFoundError("x")) == "not-found"
    assert service._reason_for(page, LoginError("x")) == "auth"
    assert service._reason_for(page, ConfirmationError("x")) == "timeout"
    assert service._reason_for(page, ActionNotAvailableError("x")) == "other"
    assert service._reason_for(page, NavigationError("x")) == "other"
    assert service._reason_for(page, RuntimeError("x")) == "other"
