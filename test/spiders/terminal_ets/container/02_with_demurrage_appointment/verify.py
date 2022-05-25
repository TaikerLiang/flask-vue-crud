from typing import List

from crawler.core_terminal.items import TerminalItem


def verify(results: List):
    assert results[0] == TerminalItem(
        container_no="EMCU5268400",
        ready_for_pick_up="No",
        available="No",
        customs_release="Release",
        appointment_date="2020-08-10 00:00~",
        last_free_day="20200810",
        demurrage="0",
        carrier="EGLV",
        container_spec="40'/Reefer/9'6\"",
        holds="No",
        cy_location="Gate Out",
        yard_location="Gate Out",
        # extra field name
        service="Local Port/Door Cargo",
        carrier_release="Release",
        tmf="Release",
        demurrage_status="Release",
        # not on html
        freight_release="Release",
    )
