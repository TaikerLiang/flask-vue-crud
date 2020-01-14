from pathlib import Path

import pytest
from scrapy import Request
from scrapy.http import TextResponse

from crawler.core_carrier.exceptions import CarrierInvalidMblNoError
from crawler.spiders.carrier_maeu_mccq_safm import MainInfoRoutingRule, CarrierSafmSpider
from test.spiders.carrier_maeu_mccq_safm.safm import main_info
from test.spiders.utils import extract_url_from


@pytest.fixture
def sample_loader(sample_loader):
    sample_path = Path(__file__).parent
    sample_loader.setup(sample_package=main_info, sample_path=sample_path)
    return sample_loader


@pytest.mark.parametrize('sub,mbl_no,', [
    ('01_single_container_not_finish', '712027741'),
    ('02_multi_containers_not_finish', '712044685'),
])
def test_main_info_routing_rule(sub, mbl_no, sample_loader):
    jsontext = sample_loader.read_file(sub, 'sample.json')

    routing_request = MainInfoRoutingRule.build_routing_request(
        mbl_no=mbl_no, url_format=CarrierSafmSpider.base_url_format)
    url = extract_url_from(routing_request=routing_request)

    response = TextResponse(
        url=url,
        body=jsontext,
        encoding='utf-8',
        request=Request(
            url=url,
        )
    )

    routing_rule = MainInfoRoutingRule()
    results = list(routing_rule.handle(response=response))

    verify_module = sample_loader.load_sample_module(sub, 'verify')
    verify_module.verify(results=results)


@pytest.mark.parametrize('sub,mbl_no,expect_exception', [
    ('e01_invalid_mbl_no', '606809321', CarrierInvalidMblNoError),
])
def test_main_info_handler_mbl_no_error(sub, mbl_no, expect_exception, sample_loader):
    jsontext = sample_loader.read_file(sub, 'sample.json')

    routing_request = MainInfoRoutingRule.build_routing_request(
        mbl_no=mbl_no, url_format=CarrierSafmSpider.base_url_format)
    url = extract_url_from(routing_request=routing_request)

    response = TextResponse(
        url=url,
        body=jsontext,
        encoding='utf-8',
        request=Request(
            url=url,
        )
    )

    routing_rule = MainInfoRoutingRule()

    with pytest.raises(expect_exception):
        list(routing_rule.handle(response=response))
