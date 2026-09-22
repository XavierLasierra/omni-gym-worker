import time
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright
from app.logging import get_logger
from app.utils.strings import normalize_class_name
from app.utils.url import is_allowed_gym_url
from app.utils.exceptions import (
    BookingError, NavigationError, ClassNotFoundError,
    ActionNotAvailableError, LoginError, ConfirmationError
)

logger = get_logger("booking_service")

TIMEOUTS = {"NAV": 45000, "ELEMENT": 45000, "LOAD": 45000, "SUCCESS": 180000}

SELECTORS = {
    "NEXT_WEEK": 'div.selector-fechas div[data-accion="fechaadelante"], div.box-calendario div.pull-right',
    "RESERVAR_MODAL": ".btn-reservar:visible, button:has-text('Reservar'), button:has-text('Inscribirme'), button:has-text(\"Inscriure'm\")",
    "CONFIRM_BTN": ".contenedor-botonera-modulo .btn-siguiente:visible, button:has-text('Confirmar'), button:has-text('Reservar')",
    "SUCCESS": ", ".join([
        ":text('Operación confirmada correctamente')",
        ":text('Operació confirmada correctament')",
        "#botonContinuar:has-text('Mis Clases')",
        "#botonContinuar:has-text('Les Meves Classes')"
    ]),
    "ERRORS": ".alert-danger, .error, .text-danger, .message-error",
    "EARLY_ERROR": ", ".join([
        ":text('No se pueden realizar reservas con una antelación superior a 2 días')",
        ":text('No es poden realitzar reserves amb una antel·lació superior a 2 dies')"
    ])
}

class BookingService:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def book_class(self, class_data: dict):
        """Main entry point for the booking automation flow."""
        try:
            gym_url = class_data.get('gym_url')
            username = class_data.get('gym_username')
            password = class_data.get('gym_password')
            class_name = class_data.get('class_name')
            class_time = class_data.get('class_time')
            target_date_str = class_data.get('target_date')
            booking_window = int(class_data.get('booking_window_hours', 48))
            target_dt = datetime.strptime(f"{target_date_str} {class_time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Europe/Madrid"))
            release_time = target_dt - timedelta(hours=booking_window)

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_context(locale="es-ES").new_page()

                try:
                    self._navigate_to_schedule(page, gym_url)
                    self._find_and_click_class(page, target_dt.date(), class_name, class_time)
                    self._handle_login(page, username, password)
                    self._wait_until_released(release_time)
                    self._confirm_booking(page)
                    return True, "Success", None
                except BookingError as e:
                    return self._handle_error(page, e)
                except Exception as e:
                    return self._handle_error(page, e)
                finally:
                    browser.close()
        except Exception as e:
            logger.error(f"Initialization failure: {e}")
            return False, f"Error de inicialización: {str(e)}", None

    def _click(self, locator, error_msg, exc=BookingError):
        """Helper to click an element with error handling."""
        try:
            locator.first.click(timeout=TIMEOUTS["ELEMENT"])
        except Exception:
            raise exc(error_msg)

    def _navigate_to_schedule(self, page, gym_url):
        url = f"{gym_url.rstrip('/')}/reserva-clases"
        if not is_allowed_gym_url(url):
            raise NavigationError("URL de gimnasio no permitida")
        logger.info(f"Navigating: {url}")
        try:
            page.goto(url, wait_until="load", timeout=TIMEOUTS["NAV"])
        except Exception:
            raise NavigationError("Error al navegar a la agenda")

    def _find_and_click_class(self, page, target_date, class_name, class_time):
        target_iso = target_date.strftime("%Y-%m-%d")
        logger.info(f"Locating {class_name} on {target_iso} @ {class_time[:5]}...")

        # Navigate to next week if needed
        if target_date.isocalendar()[:2] > datetime.now(ZoneInfo("Europe/Madrid")).isocalendar()[:2]:
            logger.info("Switching to next week...")
            self._click(page.locator(SELECTORS["NEXT_WEEK"]), "No se pudo navegar a la siguiente semana", NavigationError)
            time.sleep(2)

        # Find classes for the specific day and time
        classes_locator = page.locator(f"div.clase.clase-selector[data-idfecha='{target_iso}']").filter(has_text=class_time[:5])

        try:
            classes_locator.first.wait_for(state="visible", timeout=10000)
        except Exception:
            raise ClassNotFoundError("Clase no encontrada (fecha o hora sin clases)")

        target_class = None
        normalized_target = normalize_class_name(class_name)
        for cls in classes_locator.all():
            if normalized_target in normalize_class_name(cls.inner_text()):
                target_class = cls
                break

        if target_class is None:
            raise ClassNotFoundError("Clase no encontrada (nombre incorrecto)")

        self._click(target_class, "Clase no encontrada", ClassNotFoundError)
        self._click(page.locator(SELECTORS["RESERVAR_MODAL"]), "Botón 'Reservar' no disponible", ActionNotAvailableError)

    def _handle_login(self, page, username, password):
        logger.info("Handling login...")
        try:
            page.wait_for_selector('#email', timeout=TIMEOUTS["ELEMENT"])
        except Exception:
            raise LoginError("Error al cargar el formulario de acceso")

        page.fill('#email', username)
        page.fill('#password', password)
        page.keyboard.press('Enter')

        try:
            page.wait_for_function("() => !document.querySelector('#email')", timeout=10000)
        except Exception:
            error_el = page.locator(SELECTORS["ERRORS"]).first
            if error_el.is_visible():
                raise LoginError(f"Inicio de sesión fallido: {error_el.inner_text()}")
            logger.warning("Login form still visible after timeout.")

    def _wait_until_released(self, release_time):
        target_time = release_time + timedelta(seconds=random.uniform(1, 2))
        now = datetime.now(ZoneInfo("Europe/Madrid"))
        if now < target_time:
            wait_s = min((target_time - now).total_seconds(), 300)
            logger.info(f"Waiting {wait_s:.1f}s for booking release, release time {target_time.strftime('%H:%M:%S')}...")
            time.sleep(wait_s)
        else:
            logger.info("Already inside the booking period.")

    def _confirm_booking(self, page):
        logger.info("Finalizing booking confirmation...")
        max_retries = 5

        for attempt in range(max_retries):
            logger.info(f"Booking confirmation attempt {attempt + 1}/{max_retries}")
            self._click(page.locator(SELECTORS["CONFIRM_BTN"]), "Botón de confirmación no encontrado", ConfirmationError)

            success_loc = page.locator(SELECTORS["SUCCESS"]).first
            error_loc = page.locator(SELECTORS["EARLY_ERROR"]).first

            try:
                success_loc.or_(error_loc).wait_for(state="visible", timeout=TIMEOUTS["SUCCESS"])
            except Exception:
                raise ConfirmationError("No se recibió confirmación de la reserva")

            if success_loc.is_visible():
                logger.info("Booking request completed successfully.")
                return
            elif error_loc.is_visible():
                if attempt < max_retries - 1:
                    logger.warning("Too early error detected. Waiting 30s and retrying...")
                    try:
                        page.reload(wait_until="load", timeout=TIMEOUTS["NAV"])
                    except Exception:
                        logger.warning("Page reload failed, but proceeding anyway.")
                    time.sleep(30)
                else:
                    raise ConfirmationError(f"Error de antelación persistente tras {max_retries} intentos")

    def _handle_error(self, page, e):
        screenshot_bytes = None
        try:
            # Capture the screenshot as raw bytes to ship back to the Hub.
            screenshot_bytes = page.screenshot(full_page=True)
        except Exception as screenshot_err:
            logger.error(f"Failed to capture screenshot: {screenshot_err}")

        try:
            # Attempt to gather UI errors
            errors = page.locator(SELECTORS["ERRORS"]).all_inner_texts()
            if errors:
                logger.error(f"UI Errors detected: {errors}")
        except Exception:
            pass

        logger.error(f"Flow failed at {page.url} (Title: {page.title()}) - Error: {str(e)}")

        # If it was a BookingError, we use its message, otherwise the exception string
        msg = e.message if hasattr(e, 'message') else str(e)
        return False, f"Automation failed: {msg}", screenshot_bytes
