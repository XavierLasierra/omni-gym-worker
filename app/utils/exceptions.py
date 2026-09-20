class BookingError(Exception):
    """
    Base exception for booking-related errors.
    Contains a Spanish message for notification purposes.
    """
    def __init__(self, message="Error desconocido en la reserva"):
        self.message = message
        super().__init__(self.message)

class NavigationError(BookingError):
    """Error upon during initial navigation to the gym URLs."""
    pass

class ClassNotFoundError(BookingError):
    """Specific error when the target class cannot be located."""
    pass

class ActionNotAvailableError(BookingError):
    """Error when the booking action is not available for a specific class."""
    pass

class LoginError(BookingError):
    """Authentication related failures."""
    pass

class ConfirmationError(BookingError):
    """Errors during the final confirmation phase."""
    pass
