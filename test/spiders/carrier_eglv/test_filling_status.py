from pathlib import Path

import pytest
from scrapy import Request
from scrapy.http import TextResponse

from crawler.core_carrier.rules import RuleManager
from crawler.spiders.carrier_eglv import CarrierEglvSpider, FilingStatusRoutingRule
from test.spiders.carrier_eglv import samples_filling_status


@pytest.fixture
def sample_loader(sample_loader):
    sample_path = Path(__file__).parent / 'samples_filling_status'
    sample_loader.setup(sample_package=samples_filling_status, sample_path=sample_path)
    return sample_loader


@pytest.mark.parametrize('sub,mbl_no,', [
    ('01_only_us', '003902245109'),
    ('02_ca_and_us', '143986250473'),
])
def test_filing_status_handler(sub, mbl_no, sample_loader):
    html_file = str(sample_loader.build_file_path(sub, 'sample.html'))
    with open(html_file, 'r', encoding='utf-8') as fp:
        html_text = fp.read()

    response = TextResponse(
        url='https://www.shipmentlink.com/servlet/TDB1_CargoTracking.do',
        body=html_text,
        encoding='utf-8',
        request=Request(
            url='https://www.shipmentlink.com/servlet/TDB1_CargoTracking.do',
            meta={
                RuleManager.META_CARRIER_CORE_RULE_NAME: FilingStatusRoutingRule.name,
            }
        )
    )

    spider = CarrierEglvSpider(mbl_no=mbl_no)
    results = list(spider.parse(response=response))

    verify_module = sample_loader.load_sample_module(sub, 'verify')
    verifier = verify_module.Verifier()
    verifier.verify(results=results)
