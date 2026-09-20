import re
import time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from app.logging import get_logger
from app.utils.exceptions import NavigationError

logger = get_logger("scraper_service")

TIMEOUTS = {"NAV": 30000, "ELEMENT": 30000}
SELECTORS = {
    "NEXT_WEEK": 'div.selector-fechas div[data-accion="fechaadelante"], div.box-calendario div.pull-right',
}

class ScraperService:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def scrape_gym(self, gym_url: str, start_date=None):
        """Scrapes the timetable of a given gym for 7 days starting from start_date."""
        scraped_data = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_context(locale="es-ES").new_page()

                try:
                    self._navigate_to_schedule(page, gym_url)
                    
                    # 1. Scrape current view
                    scraped_data = self._extract_classes(page)
                    
                    # 2. Switch to next week
                    logger.info("Switching to next week...")
                    next_button = page.locator(SELECTORS["NEXT_WEEK"]).first
                    if next_button.is_visible():
                        next_button.click(timeout=TIMEOUTS["ELEMENT"])
                        time.sleep(2) # Give UI time to refresh
                        # Wait for classes to be visible again if there are any
                        try:
                            page.wait_for_selector('div.clase', timeout=TIMEOUTS["ELEMENT"])
                        except:
                            logger.warning("No classes found on second week page.")
                        
                        # 3. Scrape next week and combine
                        scraped_data += self._extract_classes(page)
                    else:
                        logger.warning("Next week button not found or not visible.")

                    # 4. Filter for 7 days window
                    if start_date is None:
                        start_date = datetime.now().date()
                    delta_end = start_date + timedelta(days=7)
                    
                    filtered_data = []
                    for c in scraped_data:
                        try:
                            class_date = datetime.strptime(c['raw_fecha'], "%Y-%m-%d").date()
                            if start_date <= class_date < delta_end:
                                filtered_data.append(c)
                        except (ValueError, KeyError):
                            continue
                    
                    unique_classes = {}
                    for c in filtered_data:
                        key = (c["day_of_week"], c["class_time"], c["class_name"])
                        if key not in unique_classes:
                            unique_classes[key] = c
                            
                    unique_classes_list = list(unique_classes.values())
                    if unique_classes_list:
                        # Sort by date and time to find first and last
                        sorted_classes = sorted(unique_classes_list, key=lambda x: (x.get('raw_fecha', ''), x.get('class_time', '')))
                        first = sorted_classes[0]
                        last = sorted_classes[-1]
                        logger.info(f"Scraped range for gym: {first.get('raw_fecha')} {first.get('class_time')} to {last.get('raw_fecha')} {last.get('class_time')}")

                    logger.info(f"Final 7-day schedule has {len(unique_classes_list)} entries.")
                    return True, unique_classes_list
                except Exception as e:
                    return self._handle_error(page, e)
                finally:
                    browser.close()
        except Exception as e:
            logger.error(f"Initialization failure: {e}")
            return False, []

    def _navigate_to_schedule(self, page, gym_url: str):
        url = f"{gym_url.rstrip('/')}/reserva-clases"
        logger.info(f"Navigating to schedule: {url}")
        try:
            page.goto(url, wait_until="load", timeout=TIMEOUTS["NAV"])
            # Give UI time to render fully
            page.wait_for_selector('div.clase', timeout=TIMEOUTS["ELEMENT"])
        except Exception:
            raise NavigationError("Error al navegar a la agenda o no se encontraron clases")

    def _extract_classes(self, page) -> list:
        logger.info("Extracting classes from schedule...")
        scraped = []
        
        clase_locators = page.locator('div.clase-selector:visible, div.clase:visible').all()
        logger.info(f"Found {len(clase_locators)} visible class elements.")

        for clase_el in clase_locators:
            try:
                # 1. Date and Time from attributes
                fecha_str = clase_el.get_attribute("data-idfecha")
                hora_inicio = clase_el.get_attribute("data-horainicio")
                
                if not fecha_str or not hora_inicio:
                    continue

                # 2. Day of week based on the date string
                try:
                    dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                    day_of_week = dt.weekday() # 0 = Monday, 6 = Sunday
                except ValueError:
                    continue
                
                # 3. Class Name
                # Priority: .nombre div with tooltip title -> .nombre text -> fallback
                class_name = ""
                nombre_loc = clase_el.locator(".nombre [data-toggle='tooltip']")
                if nombre_loc.count() > 0:
                    class_name = nombre_loc.first.get_attribute("title") or nombre_loc.first.inner_text().strip()
                
                if not class_name:
                    nombre_loc = clase_el.locator(".nombre")
                    if nombre_loc.count() > 0:
                        class_name = nombre_loc.first.inner_text().strip()

                if not class_name:
                    # Fallback heuristic: find a line that has no numbers in inner_text
                    texto_completo = clase_el.inner_text().strip()
                    lines = [line.strip() for line in texto_completo.split('\n') if line.strip()]
                    for line in lines:
                        if not re.search(r'\d', line):
                            class_name = line
                            break
                    if not class_name and len(lines) > 1:
                        class_name = lines[1] # usually second line
                
                sala = ""
                sala_loc = clase_el.locator(".sala-monitor .text, .sala .texto, .sala")
                if sala_loc.count() > 0:
                    sala = sala_loc.first.inner_text().strip()

                monitor = ""
                monitor_loc = clase_el.locator(".monitor + .texto")
                if monitor_loc.count() > 0:
                    monitor = monitor_loc.first.text_content().strip()
                    
                # Clean up monitor string if it accidentally grabbed icon text or extra spaces
                if monitor:
                    # Sometimes text_content grabs multiple lines if there are nested elements
                    monitor = monitor.replace('\n', ' ').strip()
                        
                if hora_inicio and ":" in hora_inicio:
                    time_parts = hora_inicio.split(":")
                    if len(time_parts) >= 2:
                        hora_inicio = f"{int(time_parts[0]):02d}:{int(time_parts[1]):02d}"

                if class_name:
                    scraped.append({
                        "day_of_week": day_of_week,
                        "class_time": hora_inicio,
                        "class_name": class_name,
                        "sala": sala,
                        "monitor": monitor,
                        "raw_fecha": fecha_str
                    })
            except Exception as e:
                # ignore single class parsing errors
                continue
                
        # Deduplicate classes that fall on the same time+day+name (e.g. if we scrape multiple weeks somehow)
        unique_classes = {}
        for c in scraped:
            key = (c["day_of_week"], c["class_time"], c["class_name"])
            if key not in unique_classes:
                unique_classes[key] = c
                
        unique_classes_list = list(unique_classes.values())
        if unique_classes_list:
            sample = unique_classes_list[0]
            logger.info(f"Sample parsed class - Name: {sample.get('class_name')}, Monitor: '{sample.get('monitor')}', Sala: '{sample.get('sala')}'")

        logger.info(f"Extracted {len(unique_classes)} unique schedule entries.")
        return unique_classes_list

    def _handle_error(self, page, e):
        logger.error(f"Scrape failed at {page.url} (Title: {page.title()}) {str(e)}")
        return False, []
