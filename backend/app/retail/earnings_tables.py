"""Read original statement rows; quarterly and annual columns are never conflated."""

import re
from decimal import Decimal
from html.parser import HTMLParser


class StatementTables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.stack = []
        self.rows = []
        self.cells = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.stack.append([])
        elif tag == "tr" and self.stack:
            self.rows.append([])
        elif tag in {"td", "th"} and self.rows:
            self.cells.append([])

    def handle_data(self, data):
        if self.cells:
            self.cells[-1].append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cells and self.rows:
            self.rows[-1].append(" ".join(" ".join(self.cells.pop()).split()))
        elif tag == "tr" and self.rows and self.stack:
            self.stack[-1].append(self.rows.pop())
        elif tag == "table" and self.stack:
            self.tables.append(self.stack.pop())


def statement_tables(body: bytes):
    parser = StatementTables()
    parser.feed(body.decode("utf-8", "replace"))
    return parser.tables


def numeric_cells(row: list[str]):
    values = []
    for value in row:
        value = value.strip().replace("$", "").replace(",", "").replace("\u2212", "-").strip()
        if re.fullmatch(r"\(?-?\d+(?:\.\d+)?\)?", value):
            values.append(Decimal(value.strip("()")) * (-1 if value.startswith("(") else 1))
    return values


def selected_income_statement(body: bytes):
    candidates = []
    for table in statement_tables(body):
        revenue = eps = None
        for row in table:
            label = next((cell for cell in row if cell.strip()), "").casefold().strip().rstrip(":")
            label = re.sub(r"\s*\(\d+\)$", "", label)
            if (
                label in {"revenue", "total revenue", "net sales", "total net sales"}
                and revenue is None
            ):
                values = numeric_cells(row)
                if values:
                    revenue = values
            if label == "diluted" and eps is None:
                values = numeric_cells(row)
                if values:
                    eps = values
        if revenue is not None and eps is not None:
            candidates.append(
                {
                    "revenue_columns": [str(v) for v in revenue],
                    "diluted_eps_columns": [str(v) for v in eps],
                    "table_text": " ".join(" ".join(row) for row in table)[:2500],
                }
            )
    return candidates
