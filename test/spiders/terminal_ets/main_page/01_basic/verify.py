from typing import List

from crawler.core_terminal.request_helpers import RequestOption


def verify(results: List):
    assert isinstance(results[0], RequestOption)
    assert results[0].rule_name == 'CAPTCHA'
    assert results[0].meta['verify_key'] == '832324'
