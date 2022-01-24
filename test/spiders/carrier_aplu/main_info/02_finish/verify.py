from crawler.core_carrier.items import MblItem, ContainerItem, ContainerStatusItem, LocationItem


def verify(results):
    results.pop(0)

    assert results[0] == MblItem(
        por=LocationItem(name=None),
        pol=LocationItem(name="XIAMEN (CN)"),
        pod=LocationItem(name="LOS ANGELES, CA (US)"),
        final_dest=LocationItem(name=None),
        eta=None,
        ata="Thu 25 Jul 2019 19:14",
    )

    assert results[1] == ContainerItem(
        container_key="TCLU9692715",
        container_no="TCLU9692715",
    )

    assert results[2] == ContainerStatusItem(
        container_key="TCLU9692715",
        local_date_time="Wed 03 Jul 2019 07:21",
        description="Empty to shipper",
        location=LocationItem(name="XIAMEN"),
        facility="",
        est_or_actual="A",
    )

    assert results[7] == ContainerStatusItem(
        container_key="TCLU9692715",
        local_date_time="Fri 02 Aug 2019 14:15",
        description="Empty in depot",
        location=LocationItem(name="LOS ANGELES, CA"),
        facility="TRAPAC TERMINAL",
        est_or_actual="A",
    )


def multi_verify(results):
    results.pop(0)

    assert results[0] == MblItem(
        por=LocationItem(name=None),
        pol=LocationItem(name="XIAMEN (CN)"),
        pod=LocationItem(name="LOS ANGELES, CA (US)"),
        final_dest=LocationItem(name=None),
        eta=None,
        ata="Thu 25 Jul 2019 19:14",
        task_id=1,
    )

    assert results[1] == ContainerItem(
        container_key="TCLU9692715",
        container_no="TCLU9692715",
        task_id=1,
    )

    assert results[2] == ContainerStatusItem(
        container_key="TCLU9692715",
        local_date_time="Wed 03 Jul 2019 07:21",
        description="Empty to shipper",
        location=LocationItem(name="XIAMEN"),
        facility="",
        est_or_actual="A",
        task_id=1,
    )

    assert results[7] == ContainerStatusItem(
        container_key="TCLU9692715",
        local_date_time="Fri 02 Aug 2019 14:15",
        description="Empty in depot",
        location=LocationItem(name="LOS ANGELES, CA"),
        facility="TRAPAC TERMINAL",
        est_or_actual="A",
        task_id=1,
    )
