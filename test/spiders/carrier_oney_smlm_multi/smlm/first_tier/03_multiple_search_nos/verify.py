from crawler.core_carrier.items import ExportErrorData
from crawler.core_carrier.oney_smlm_multi_share_spider import NextRoundRoutingRule
from crawler.core_carrier.request_helpers import RequestOption
from crawler.spiders.carrier_smlm_multi import CarrierSmlmSpider
from crawler.core_carrier.exceptions import CARRIER_RESULT_STATUS_ERROR


def verify(results):
    assert results[0] == ExportErrorData(
        mbl_no="SHSB1FY71701",
        status=CARRIER_RESULT_STATUS_ERROR,
        detail="Data was not found",
        task_id=1,
    )

    assert isinstance(results[19], RequestOption)
    assert results[19].url == "https://eval.edi.hardcoretech.co/c/livez"
    assert results[19].rule_name == NextRoundRoutingRule.name
    assert results[19].meta == {
        "search_nos": ["SHSB1FY71701", "NJBH1A243500"],
        "task_ids": [1, 2],
        "base_url": CarrierSmlmSpider.base_url,
    }
