from crawler.core_carrier.items import MblItem, ContainerItem, ContainerStatusItem, LocationItem


def verify(results):
    assert results[0] == MblItem(
        mbl_no='606809323',
        por=LocationItem(name='Shanghai Wai Gao Qiao Terminal -- Shanghai (Shanghai, CN)'),
        final_dest=LocationItem(name='Cin-Csx -- Cincinnati (Ohio, US)'),
        task_id='1',
    )

    assert results[1] == ContainerItem(
        container_key='FXLU1794508', container_no='FXLU1794508', final_dest_eta='2019-12-17T08:00:00.000',
        task_id='1',
    )

    assert results[2] == ContainerStatusItem(
        container_key='FXLU1794508',
        description='GATE-IN',
        local_date_time='2019-11-15T21:38:00.000',
        location=LocationItem(name='Shanghai Wai Gao Qiao Terminal -- Shanghai (Shanghai, CN)'),
        vessel='HYUNDAI TOKYO F8V',
        voyage='121E',
        est_or_actual='A',
        task_id='1',
    )

    assert results[9] == ContainerStatusItem(
        container_key='FXLU1794508',
        description='GATE-OUT',
        local_date_time='2019-12-17T08:00:00.000',
        location=LocationItem(name='Cin-Csx -- Cincinnati (Ohio, US)'),
        vessel=None,
        voyage=None,
        est_or_actual='E',
        task_id='1',
    )

    assert results[10] == ContainerItem(
        container_key='FXLU1795947', container_no='FXLU1795947', final_dest_eta='2019-12-17T08:00:00.000', task_id='1',
    )

    assert results[11] == ContainerStatusItem(
        container_key='FXLU1795947',
        description='GATE-IN',
        local_date_time='2019-11-16T23:53:00.000',
        location=LocationItem(name='Shanghai Wai Gao Qiao Terminal -- Shanghai (Shanghai, CN)'),
        vessel='HYUNDAI TOKYO F8V',
        voyage='121E',
        est_or_actual='A',
        task_id='1',
    )

    assert results[18] == ContainerStatusItem(
        container_key='FXLU1795947',
        description='GATE-OUT',
        local_date_time='2019-12-17T08:00:00.000',
        location=LocationItem(name='Cin-Csx -- Cincinnati (Ohio, US)'),
        vessel=None,
        voyage=None,
        est_or_actual='E',
        task_id='1',
    )
