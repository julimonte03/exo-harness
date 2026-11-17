"""CSV export of invoice totals, one row per invoice."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from typing import TextIO

from invoices import InvoiceError
from invoices.billing.totals import Totals

COLUMNS = ("number", "subtotal", "discount", "tax", "total")


def export(rows: Iterable[tuple[str, Totals]], stream: TextIO) -> int:
    """Write a header and one row per invoice; return how many invoices were written."""
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(COLUMNS)
    count = 0
    for number, totals in rows:
        if totals.total < 0:
            raise InvoiceError(f"invoice {number} has a negative total")
        writer.writerow([number, totals.subtotal, totals.discount, totals.tax, totals.total])
        count += 1
    return count
