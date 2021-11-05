from crawler.core_carrier.items import MblItem, ContainerItem, ContainerStatusItem, LocationItem


def verify(results):
    assert results[0] == ContainerItem(
        container_key="GLDU7632978",
        container_no="GLDU7632978",
    )

    assert results[1] == ContainerStatusItem(
        container_key="GLDU7632978",
        description="Empty received at CY",
        local_date_time="10/10/2019",
        location=LocationItem(name="LOS ANGELES, US"),
        vessel=None,
        voyage=None,
        est_or_actual="A",
    )

    assert results[10] == ContainerStatusItem(
        container_key="GLDU7632978",
        description="Export at barge yard",
        local_date_time="05/09/2019",
        location=LocationItem(name="ZHAPU, CN"),
        vessel=None,
        voyage=None,
        est_or_actual="A",
    )

    assert results[12] == MblItem(
        mbl_no="MEDUN4194175",
        pol=LocationItem(name="NINGBO, CN"),
        pod=LocationItem(name="LONG BEACH, US"),
        etd="18/09/2019",
        vessel="MSC BERYL",
        place_of_deliv=LocationItem(name="LONG BEACH, US"),
        latest_update="05.11.2021 at 03:23 Central Europe Standard Time",
    )
