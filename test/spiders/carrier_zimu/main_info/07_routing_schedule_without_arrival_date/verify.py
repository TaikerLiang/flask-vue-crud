from crawler.core_carrier.items_new import (
    ContainerItem,
    ContainerStatusItem,
    LocationItem,
    MblItem,
    VesselItem,
)


def verify(results):
    assert results[0] == VesselItem(
        task_id="1",
        vessel_key=0,
        vessel="ZIM ANTWERP",
        voyage="53",
        pol=LocationItem(name="WILMINGTON (NC), U.S.A."),
        pod=LocationItem(name="NINGBO (ZJ), CHINA. PEOPLE'S REPUBLIC"),
        etd="08-Nov-2019",
        eta=None,
    )

    assert results[1] == VesselItem(
        task_id="1",
        vessel_key=1,
        vessel="KUO CHANG",
        voyage="562",
        pol=LocationItem(name="NINGBO (ZJ), CHINA. PEOPLE'S REPUBLIC"),
        pod=LocationItem(name="KEELUNG, TAIWAN"),
        etd="18-Dec-2019",
        eta="21-Dec-2019",
    )

    assert results[2] == MblItem(
        task_id="1",
        mbl_no="ZIMUORF0941773",
        vessel="KUO CHANG",
        voyage="562",
        por=LocationItem(name=None),
        pol=LocationItem(name="WILMINGTON (NC), U.S.A."),
        pod=LocationItem(name="KEELUNG, TAIWAN"),
        place_of_deliv=LocationItem(un_lo_code=None, name=None),
        etd="08-Nov-2019",
        eta="21-Dec-2019",
        deliv_eta=None,
        deliv_ata=None,
    )

    assert results[3] == ContainerItem(
        task_id="1",
        container_key="ZIMU1413332",
        container_no="ZIMU1413332",
        terminal_pod=LocationItem(name=None),
    )

    assert results[4] == ContainerStatusItem(
        task_id="1",
        container_key="ZIMU1413332",
        description="Vessel departure from Port of Loading to Transshipment Port",
        local_date_time="09-Nov-2019 02:52",
        location=LocationItem(name="WILMINGTON (NC), U.S.A."),
    )
