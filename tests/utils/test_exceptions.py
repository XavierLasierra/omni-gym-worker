import pytest
from app.utils.exceptions import (
    BookingError,
    NavigationError,
    ClassNotFoundError,
    ActionNotAvailableError,
    LoginError,
    ConfirmationError,
)

def test_booking_error_default_message():
    err = BookingError()
    assert err.message == "Error desconocido en la reserva"
    assert str(err) == "Error desconocido en la reserva"

def test_booking_error_custom_message():
    err = BookingError("Custom error message")
    assert err.message == "Custom error message"
    assert str(err) == "Custom error message"

def test_exception_inheritance():
    assert issubclass(NavigationError, BookingError)
    assert issubclass(ClassNotFoundError, BookingError)
    assert issubclass(ActionNotAvailableError, BookingError)
    assert issubclass(LoginError, BookingError)
    assert issubclass(ConfirmationError, BookingError)

def test_custom_exception_messages():
    err1 = NavigationError("Could not reach site")
    assert err1.message == "Could not reach site"
    assert isinstance(err1, BookingError)

    err2 = ClassNotFoundError()
    assert err2.message == "Error desconocido en la reserva"
