from crawler.core_carrier.items import ContainerItem


def verify(results):
    assert results[0] == ContainerItem(
        container_key='DFSU7597714',
        container_no='DFSU7597714',
    )

    assert results[3] == ContainerItem(
        container_key='WHSU5323281',
        container_no='WHSU5323281',
    )
