from pathlib import Path

import pytest
from scrapy import Request
from scrapy.http import TextResponse

from crawler.core_terminal.cloud1_share_spider import (
    ConfigureSettingsRule,
    ContainerRoutingRule,
)
from test.spiders.terminal_cloud1_k323 import container


@pytest.fixture
def sample_loader(sample_loader):
    sample_path = Path(__file__).parent
    sample_loader.setup(sample_package=container, sample_path=sample_path)
    return sample_loader


@pytest.mark.parametrize(
    "sub,container_no,url",
    [
        (
            "01_basic",
            "BMOU4848347",
            "https://cloud1.cargomanager.com/warehousingARWP/availability/details.jsp?code=CHI&link=C22384",
        ),
        (
            "02_container_no_mismatch",
            "SEGU5842736",
            "https://cloud1.cargomanager.com/warehousingARWP/availability/details.jsp?code=CHI&link=C22384",
        ),
    ],
)
def test_container_handle(sub, container_no, url, sample_loader):
    json_text = sample_loader.read_file(sub, "sample.html")

    option = ContainerRoutingRule.build_request_option(container_no=container_no, url=url)

    response = TextResponse(
        url=option.url,
        body=json_text,
        encoding="utf-8",
        request=Request(
            url=option.url,
            meta=option.meta,
        ),
    )

    rule = ContainerRoutingRule()
    results = list(rule.handle(response=response))

    verify_module = sample_loader.load_sample_module(sub, "verify")
    verify_module.verify(results=results)


@pytest.mark.parametrize(
    "sub,container_no,url_code,code",
    [
        ("03_data_not_found", "SEGU5842736", "ARWP", "ARWP"),
    ],
)
def test_container_not_found(sub, container_no, url_code, code, sample_loader):
    json_text = sample_loader.read_file(sub, "sample.html")

    option = ConfigureSettingsRule.build_request_option(container_no=container_no, url_code=url_code, code=code)

    response = TextResponse(
        url=option.url,
        body=json_text,
        encoding="utf-8",
        request=Request(
            url=option.url,
            meta=option.meta,
        ),
    )

    rule = ConfigureSettingsRule()
    results = list(rule.handle(response=response))

    verify_module = sample_loader.load_sample_module(sub, "verify")
    verify_module.verify(results=results)
