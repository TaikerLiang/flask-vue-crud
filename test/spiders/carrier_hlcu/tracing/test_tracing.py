from pathlib import Path

import pytest
from scrapy import Request
from scrapy.http import TextResponse

from crawler.core_carrier.rules import RuleManager
from crawler.spiders.carrier_hlcu import CarrierHlcuSpider, TracingRoutingRule
from test.spiders.carrier_hlcu import tracing


@pytest.fixture
def sample_loader(sample_loader):
    sample_path = Path(__file__).parent
    sample_loader.setup(sample_package=tracing, sample_path=sample_path)
    return sample_loader


@pytest.mark.parametrize('sub,mbl_no', [
    ('01_single_container', 'HLCUSHA1904CCVX4'),
    ('02_multi_containers', 'HLCUSHA1911AVPN9'),
])
def test_container_handler(sub, mbl_no, sample_loader):
    httptext = sample_loader.read_file(sub, 'sample.html')

    url = f'https://www.hapag-lloyd.com/en/online-business/tracing/tracing-by-booking.html?blno={mbl_no}'

    response = TextResponse(
        url=url,
        body=httptext,
        encoding='utf-8',
        request=Request(
            url=url,
            meta={
                RuleManager.META_CARRIER_CORE_RULE_NAME: TracingRoutingRule.name,
                'mbl_no': mbl_no,
                'cookies': '',
            }
        )
    )

    spider = CarrierHlcuSpider(mbl_no=mbl_no)
    results = list(spider.parse(response=response))

    verify_module = sample_loader.load_sample_module(sub, 'verify')
    verifier = verify_module.Verifier()
    verifier.verify(results=results)
