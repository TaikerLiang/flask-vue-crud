from pathlib import Path

import pytest
from scrapy import Request
from scrapy.http import TextResponse

from crawler.core_carrier.exceptions import CarrierInvalidMblNoError
from crawler.spiders.carrier_sudu import SearchRoutingRule, BasicRequestSpec
from test.spiders.carrier_sudu import search
from test.spiders.utils import extract_url_from


@pytest.fixture
def sample_loader(sample_loader):
    sample_path = Path(__file__).parent
    sample_loader.setup(sample_package=search, sample_path=sample_path)
    return sample_loader


@pytest.mark.parametrize('sub,mbl_no,expect_view,is_first', [
    ('01_parse_detail', 'SUDUN9998ALTNBPS', 'CONTAINER_DETAIL', True),
    ('02_first_in_container_list', 'SUDUN9998ALTNBPS', None, True),
])
def test_main_info_routing_rule(sub, mbl_no, expect_view, sample_loader, is_first):
    text_text = sample_loader.read_file(sub, 'sample.html')

    basic_request_spec = BasicRequestSpec(mbl_no=mbl_no, view_state='', j_idt='')
    routing_request = SearchRoutingRule.build_routing_request(
        basic_request_spec=basic_request_spec, expect_view=expect_view, is_first_process=is_first)
    url = extract_url_from(routing_request=routing_request)

    response = TextResponse(
        url=url,
        body=text_text,
        encoding='utf-8',
        request=Request(
            url=url,
            meta={
                'mbl_no': mbl_no,
                'expect_view': expect_view,
                'is_first_process': is_first,
            }
        )
    )

    routing_rule = SearchRoutingRule()
    results = list(routing_rule.handle(response=response))

    verify_module = sample_loader.load_sample_module(sub, 'verify')
    verify_module.verify(results=results)


@pytest.mark.parametrize('sub,mbl_no,expect_view,is_first,expect_exception', [
    ('e01_invalid_mbl_no', 'SUDUN9998ALTNBPU', None, True, CarrierInvalidMblNoError),
])
def test_main_info_handler_mbl_no_error(sub, mbl_no, expect_view, is_first, expect_exception, sample_loader):
    text_text = sample_loader.read_file(sub, 'sample.html')

    basic_request_spec = BasicRequestSpec(mbl_no=mbl_no, view_state='', j_idt='')
    routing_request = SearchRoutingRule.build_routing_request(
        basic_request_spec=basic_request_spec, expect_view=expect_view, is_first_process=is_first)
    url = extract_url_from(routing_request=routing_request)

    response = TextResponse(
        url=url,
        body=text_text,
        encoding='utf-8',
        request=Request(
            url=url,
            meta={
                'mbl_no': mbl_no,
                'expect_view': expect_view,
                'is_first_process': is_first
            }
        )
    )

    routing_rule = SearchRoutingRule()

    with pytest.raises(expect_exception):
        list(routing_rule.handle(response=response))
