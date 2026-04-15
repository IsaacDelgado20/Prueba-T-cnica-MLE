"""
Adaptador de Selenium para web scraping - Implementa ScraperPort.
Utiliza Selenium con Chrome remoto para manejar contenido dinámico (JavaScript).
Incluye retry con backoff exponencial y manejo seguro de recursos.
"""

import logging
import re
import time
from contextlib import contextmanager
from typing import Generator, List, Optional, Set
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException

from src.domain.entities import Document
from src.domain.ports import ScraperPort

logger = logging.getLogger(__name__)

# Extensiones de archivo a omitir
_SKIP_EXTENSIONS = frozenset({
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
    ".css", ".js", ".xml", ".zip", ".doc", ".docx", ".xls",
    ".xlsx", ".ppt", ".pptx", ".mp3", ".mp4", ".avi",
})

# Patrones de URL a omitir
_SKIP_PATTERNS = frozenset({"#", "javascript:", "mailto:", "tel:", "data:"})


class ScrapingError(Exception):
    """Error específico de scraping."""


class SeleniumScraper(ScraperPort):
    """Adaptador Selenium para web scraping con soporte de contenido dinámico."""

    def __init__(
        self,
        remote_url: str = "http://chrome:4444/wd/hub",
        page_load_timeout: int = 30,
        wait_after_load: float = 2.0,
        delay_between_pages: float = 1.0,
        max_retries: int = 2,
    ):
        self._remote_url = remote_url
        self._page_load_timeout = page_load_timeout
        self._wait_after_load = wait_after_load
        self._delay_between_pages = delay_between_pages
        self._max_retries = max_retries

    @contextmanager
    def _driver_context(self) -> Generator[webdriver.Remote, None, None]:
        """Context manager para manejo seguro del WebDriver."""
        driver = self._create_driver()
        try:
            yield driver
        finally:
            try:
                driver.quit()
            except Exception:
                pass

    def _create_driver(self) -> webdriver.Remote:
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--lang=es")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        driver = webdriver.Remote(
            command_executor=self._remote_url,
            options=options,
        )
        driver.set_page_load_timeout(self._page_load_timeout)
        return driver

    def scrape(self, url: str, max_pages: int = 20) -> List[Document]:
        """Scrapea el sitio web comenzando desde la URL dada."""
        with self._driver_context() as driver:
            documents: List[Document] = []
            visited: Set[str] = set()
            to_visit: List[str] = [url]
            base_domain = urlparse(url).netloc
            errors: int = 0

            while to_visit and len(visited) < max_pages:
                current_url = to_visit.pop(0)

                if current_url in visited:
                    continue

                doc = self._scrape_with_retry(driver, current_url)
                visited.add(current_url)

                if doc:
                    documents.append(doc)
                    logger.info(
                        "Scraped (%d/%d): %s", len(documents), max_pages, current_url
                    )
                    new_links = self._extract_links(driver, base_domain, visited)
                    to_visit.extend(new_links)
                else:
                    errors += 1

                time.sleep(self._delay_between_pages)

            logger.info(
                "Scraping completado: %d documentos de %d URLs visitadas (%d errores)",
                len(documents), len(visited), errors,
            )
            return documents

    def _scrape_with_retry(
        self, driver: webdriver.Remote, url: str
    ) -> Optional[Document]:
        """Scrapea una página con reintentos."""
        for attempt in range(1, self._max_retries + 1):
            try:
                return self._scrape_page(driver, url)
            except (WebDriverException, TimeoutException) as e:
                if attempt < self._max_retries:
                    wait = 2 ** attempt
                    logger.warning(
                        "Intento %d/%d falló para %s: %s. Reintentando en %ds...",
                        attempt, self._max_retries, url, e, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.warning("Todos los intentos fallaron para %s: %s", url, e)
            except Exception as e:
                logger.warning("Error inesperado en %s: %s", url, e)
                break
        return None

    def _scrape_page(self, driver: webdriver.Remote, url: str) -> Optional[Document]:
        """Scrapea una página individual."""
        driver.get(url)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            logger.warning("Timeout esperando body en %s", url)
            return None

        time.sleep(self._wait_after_load)

        raw_html = driver.page_source
        title = driver.title or url

        clean_text = self._clean_html(raw_html)

        if len(clean_text) < 100:
            return None

        return Document.create(
            url=url,
            title=title,
            raw_content=raw_html,
            clean_content=clean_text,
        )

    @staticmethod
    def _clean_html(html: str) -> str:
        """Limpia HTML y extrae texto relevante."""
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(
            ["script", "style", "nav", "footer", "header", "noscript", "iframe", "svg", "meta", "link"]
        ):
            tag.decompose()

        text = soup.get_text(separator="\n")

        lines = [line.strip() for line in text.splitlines()]
        clean_text = "\n".join(line for line in lines if line)

        # Colapsar múltiples líneas en blanco
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)

        return clean_text

    def _extract_links(
        self, driver: webdriver.Remote, base_domain: str, visited: Set[str]
    ) -> List[str]:
        """Extrae enlaces internos de la página actual."""
        links: Set[str] = set()
        try:
            elements = driver.find_elements(By.TAG_NAME, "a")
            for elem in elements:
                try:
                    href = elem.get_attribute("href")
                    if not href:
                        continue

                    # Omitir patrones no deseados
                    if any(p in href for p in _SKIP_PATTERNS):
                        continue

                    parsed = urlparse(href)

                    # Solo mismo dominio
                    if parsed.netloc and parsed.netloc != base_domain:
                        continue

                    # Limpiar URL (remover fragmentos y params)
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if not clean_url.startswith("http"):
                        continue

                    # Omitir archivos no-HTML
                    if any(clean_url.lower().endswith(ext) for ext in _SKIP_EXTENSIONS):
                        continue

                    if clean_url not in visited:
                        links.add(clean_url)

                except Exception:
                    continue

        except Exception as e:
            logger.warning("Error extrayendo enlaces: %s", e)

        return list(links)
