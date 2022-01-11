from pathlib import Path

import pytest
from scrapy import Request
from scrapy.http import TextResponse

from crawler.core_terminal.tideworks_share_spider import SearchContainerRoutingRule
from crawler.spiders.terminal_pomtoc_multi import TerminalPomtocSpider
from test.spiders.terminal_pomtoc_multi import search_container


@pytest.fixture
def sample_loader(sample_loader):
    sample_path = Path(__file__).parent
    sample_loader.setup(sample_package=search_container, sample_path=sample_path)
    return sample_loader


@pytest.mark.parametrize(
    "sub,container_no",
    [
        ("01_basic", "TGHU6027388"),
        ("02_invalid_container_no", "invalid_container_no"),
    ],
)
def test_search_container(sub, container_no, sample_loader):
    httptext = sample_loader.read_file(sub, "sample.html")

    option = SearchContainerRoutingRule.build_request_option(
        container_nos=[container_no],
        company_info=TerminalPomtocSpider.company_info,
        cookies={},
        token="",
    )

    response = TextResponse(
        url=option.url,
        body=httptext,
        encoding="utf-8",
        request=Request(
            url=option.url,
            meta=option.meta,
        ),
    )

    rule = SearchContainerRoutingRule()
    results = list(rule.handle(response=response))

    verify_module = sample_loader.load_sample_module(sub, "verify")
    verify_module.verify(results=results)
