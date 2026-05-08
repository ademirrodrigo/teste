from bs4 import BeautifulSoup

from ecac_automation.parser.base import BaseParser


class FiscalSummaryParser(BaseParser):
    def parse(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        return {
            "title": soup.title.string if soup.title else "",
            "tables": len(soup.find_all("table")),
            "alerts": [a.text.strip() for a in soup.select(".alert")],
        }
