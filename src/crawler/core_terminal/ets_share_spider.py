import dataclasses
import io
import json
import random
import re
from typing import Dict, List

import PIL.Image as Image
import scrapy
from anticaptchaofficial.imagecaptcha import imagecaptcha
from scrapy.http import HtmlResponse

from crawler.core.proxy import HydraproxyProxyManager
from crawler.core_terminal.base import TERMINAL_RESULT_STATUS_ERROR
from crawler.core_terminal.base_spiders import BaseMultiTerminalSpider
from crawler.core_terminal.exceptions import DriverMaxRetryError
from crawler.core_terminal.items import DebugItem, ExportErrorData, TerminalItem
from crawler.core_terminal.request_helpers import RequestOption
from crawler.core_terminal.rules import BaseRoutingRule, RuleManager


@dataclasses.dataclass
class CompanyInfo:
    email: str
    password: str


BASE_URL = "https://www.etslink.com"
MAX_RETRY_COUNT = 3
MAX_PAGE_NUM = 20


class Restart:
    pass


class EtsShareSpider(BaseMultiTerminalSpider):
    name = ""
    company_info = CompanyInfo(
        email="",
        password="",
    )

    def __init__(self, *args, **kwargs):
        super(EtsShareSpider, self).__init__(*args, **kwargs)

        rules = [
            MainPageRoutingRule(),
            CaptchaRoutingRule(),
            LoginRoutingRule(),
            ContainerRoutingRule(),
            NextRoundRoutingRule(),
        ]
        self._proxy_manager = HydraproxyProxyManager(session="share", logger=self.logger)
        self._rule_manager = RuleManager(rules=rules)
        self._retry_count = 0

    def start(self):
        yield self._prepare_start()

    def _prepare_start(self):
        if self._retry_count > MAX_RETRY_COUNT:
            raise DriverMaxRetryError()

        self._retry_count += 1

        self._proxy_manager.renew_proxy()
        unique_container_nos = list(self.cno_tid_map.keys())
        option = MainPageRoutingRule.build_request_option(
            container_no_list=unique_container_nos, company_info=self.company_info
        )
        proxy_option = self._proxy_manager.apply_proxy_to_request_option(option=option)
        return self._build_request_by(option=proxy_option)

    def parse(self, response):
        yield DebugItem(info={"meta": dict(response.meta)})

        routing_rule = self._rule_manager.get_rule_by_response(response=response)

        save_name = routing_rule.get_save_name(response=response)
        self._saver.save(to=save_name, text=response.text)

        for result in routing_rule.handle(response=response):
            if isinstance(result, TerminalItem) or isinstance(result, ExportErrorData):
                c_no = result["container_no"]
                if c_no:
                    t_ids = self.cno_tid_map[c_no]
                    for t_id in t_ids:
                        result["task_id"] = t_id
                        yield result
            elif isinstance(result, RequestOption):
                yield self._build_request_by(option=result)
            elif isinstance(result, Restart):
                yield self._prepare_start()
            else:
                raise RuntimeError()

    def _build_request_by(self, option: RequestOption):
        meta = {
            RuleManager.META_TERMINAL_CORE_RULE_NAME: option.rule_name,
            **option.meta,
        }

        if option.method == RequestOption.METHOD_POST_FORM:
            return scrapy.FormRequest(
                url=option.url,
                formdata=option.form_data,
                meta=meta,
            )

        elif option.method == RequestOption.METHOD_GET:
            return scrapy.Request(url=option.url, meta=meta, dont_filter=True)

        else:
            raise RuntimeError()


class MainPageRoutingRule(BaseRoutingRule):
    name = "MAIN_PAGE"

    @classmethod
    def build_request_option(cls, container_no_list, company_info: CompanyInfo) -> RequestOption:
        return RequestOption(
            rule_name=cls.name,
            method=RequestOption.METHOD_GET,
            url=f"{BASE_URL}",
            meta={
                "container_no_list": container_no_list,
                "company_info": company_info,
            },
        )

    def get_save_name(self, response) -> str:
        return f"{self.name}.html"

    def handle(self, response):
        container_no_list = response.meta["container_no_list"]
        company_info = response.meta["company_info"]

        verify_key = self._extract_verify_key(response=response)

        yield CaptchaRoutingRule.build_request_option(verify_key, container_no_list, company_info)

    @staticmethod
    def _extract_verify_key(response: scrapy.Selector) -> str:
        pattern = re.compile(r'&verifyKey=(?P<verify_key>\d+)"')

        script_text = response.css("script").getall()[3]
        s = pattern.search(script_text)
        verify_key = s.group("verify_key")

        return verify_key


class CaptchaRoutingRule(BaseRoutingRule):
    name = "CAPTCHA"

    @classmethod
    def build_request_option(cls, verify_key, container_no_list, company_info: CompanyInfo) -> RequestOption:
        dc = cls._get_random_number()

        return RequestOption(
            rule_name=cls.name,
            method=RequestOption.METHOD_GET,
            url=f"{BASE_URL}/waut/VerifyCodeImage.jsp?dc={dc}&verifyKey={verify_key}",
            meta={
                "container_no_list": container_no_list,
                "dc": dc,
                "verify_key": verify_key,
                "company_info": company_info,
            },
        )

    def handle(self, response):
        container_no_list = response.meta["container_no_list"]
        dc = response.meta["dc"]
        verify_key = response.meta["verify_key"]
        company_info = response.meta["company_info"]

        captcha_text = self._get_captcha_str(response.body)

        if captcha_text:
            yield LoginRoutingRule.build_request_option(
                company_info=company_info,
                captcha_text=captcha_text,
                container_no_list=container_no_list,
                dc=dc,
                verify_key=verify_key,
            )
        else:
            yield LoginRoutingRule.build_request_option(
                company_info=company_info,
                captcha_text="",
                container_no_list=container_no_list,
                dc="",
                verify_key=verify_key,
            )

    @staticmethod
    def _get_captcha_str(captcha_code):
        file_name = "captcha.jpeg"
        image = Image.open(io.BytesIO(captcha_code))
        image.save(file_name)
        # api_key = 'f7dd6de6e36917b41d05505d249876c3'
        api_key = "fbe73f747afc996b624e8d2a95fa0f84"
        solver = imagecaptcha()
        solver.set_verbose(1)
        solver.set_key(api_key)

        captcha_text = solver.solve_and_return_solution(file_name)
        if captcha_text != 0:
            return captcha_text
        else:
            print("task finished with error ", solver.error_code)
            return ""

    @staticmethod
    def _get_random_number():
        return str(int(random.random() * 10000000))


class LoginRoutingRule(BaseRoutingRule):
    name = "LOGIN"

    @classmethod
    def build_request_option(
        cls, container_no_list, company_info: CompanyInfo, captcha_text, dc, verify_key
    ) -> RequestOption:
        form_data = {
            "PI_LOGIN_ID": company_info.email,
            "PI_PASSWORD": company_info.password,
            "PI_VERIFY_CODE": captcha_text,
            "PI_VERIFY_DC": dc,
            "PI_VERIFY_KEY": verify_key,
        }

        return RequestOption(
            rule_name=cls.name,
            method=RequestOption.METHOD_POST_FORM,
            url=f"{BASE_URL}/login",
            form_data=form_data,
            meta={"container_no_list": container_no_list},
        )

    def get_save_name(self, response) -> str:
        return f"{self.name}.json"

    def handle(self, response):
        container_no_list = response.meta["container_no_list"]

        response_dict = json.loads(response.text)
        print(response_dict)
        sk = response_dict.get("_sk")
        if not sk:
            yield Restart()
            return

        yield ContainerRoutingRule.build_request_option(container_no_list=container_no_list, sk=sk)


class ContainerRoutingRule(BaseRoutingRule):
    name = "CONTAINER"

    @classmethod
    def build_request_option(cls, container_no_list, sk) -> RequestOption:
        form_data = {
            "PI_BUS_ID": "?cma_bus_id",
            "PI_TMNL_ID": "?cma_env_loc",
            "PI_CTRY_CODE": "?cma_env_ctry",
            "PI_STATE_CODE": "?cma_env_state",
            "PI_CNTR_NO": "\n".join(container_no_list[:MAX_PAGE_NUM]),
            "_sk": sk,
            "page": "1",
            "start": "0",
            "limit": "-1",
        }

        return RequestOption(
            rule_name=cls.name,
            method=RequestOption.METHOD_POST_FORM,
            url=f"{BASE_URL}/data/WIMPP003.queryByCntr.data.json?",
            form_data=form_data,
            meta={"container_no_list": container_no_list, "sk": sk},
        )

    def get_save_name(self, response) -> str:
        return f"{self.name}.json"

    def handle(self, response):
        container_no_list = response.meta["container_no_list"]

        container_info_list = self._extract_container_info(response=response)

        if self._is_container_no_error(container_info_list=container_info_list):
            if len(container_no_list) > 1:
                yield DebugItem(
                    info="Contains abnormal container_no in this round of paging, search each container_no individually"
                )
                sk = response.meta["sk"]
                for c_no in container_no_list[:MAX_PAGE_NUM]:
                    yield ContainerRoutingRule.build_request_option(container_no_list=[c_no], sk=sk)

                yield NextRoundRoutingRule.build_request_option(container_no_list=container_no_list, sk=sk)

            return

        if self._is_container_no_invalid_with_msg(container_info_list=container_info_list):
            for c_no in container_no_list[:MAX_PAGE_NUM]:
                yield ExportErrorData(
                    container_no=c_no,
                    detail="Data was not found",
                    status=TERMINAL_RESULT_STATUS_ERROR,
                )

        for container_info in container_info_list:
            if self._is_container_no_invalid_with_term_name(container_info=container_info):
                c_no = re.sub("<.*?>", "", container_info["PO_CNTR_NO"])
                yield ExportErrorData(
                    container_no=c_no,
                    detail="Data was not found",
                    status=TERMINAL_RESULT_STATUS_ERROR,
                )
            else:
                yield TerminalItem(
                    container_no=container_info["PO_CNTR_NO"],
                    ready_for_pick_up=container_info["PO_AVAILABLE_IND"],
                    customs_release=container_info["PO_USA_STATUS"],
                    appointment_date=container_info["PO_APPOINTMENT_TIME"],
                    last_free_day=container_info["PO_DM_LAST_FREE_DATE"],
                    demurrage=container_info["PO_DM_AMT_DUE"],
                    carrier=container_info["PO_CARRIER_SCAC_CODE"],
                    container_spec=(
                        f'{container_info["PO_CNTR_TYPE_S"]}/{container_info["PO_CNTR_TYPE_T"]}/'
                        f'{container_info["PO_CNTR_TYPE_H"]}'
                    ),
                    holds=container_info["PO_TMNL_HOLD_IND"],
                    cy_location=container_info["PO_YARD_LOC"],
                    # extra field name
                    service=container_info["PO_SVC_QFR_DESC"],
                    carrier_release=container_info["PO_CARRIER_STATUS"],
                    tmf=container_info["PO_TMF_STATUS"],
                    demurrage_status=container_info["PO_DM_STATUS"],
                    # not on html
                    freight_release=container_info["PO_FR_STATUS"],  # not sure
                )

        sk = response.meta["sk"]
        yield NextRoundRoutingRule.build_request_option(container_no_list=container_no_list, sk=sk)

    @staticmethod
    def _extract_container_info(response: HtmlResponse):
        response_dict = json.loads(response.text)

        container_info_list = []
        titles = response_dict["cols"]
        for resp in response_dict["data"]:
            container_info = {}
            for title_index, title in enumerate(titles):
                data_index = title_index

                title_name = title["name"]
                container_info[title_name] = resp[data_index]
            container_info_list.append(container_info)

        return container_info_list

    @staticmethod
    def _is_container_no_invalid_with_term_name(container_info: Dict):
        if container_info["PO_TERMINAL_NAME"]:
            return container_info["PO_TERMINAL_NAME"] == "<i>Record was not found!</i>"

    @staticmethod
    def _is_container_no_invalid_with_msg(container_info_list: List):
        if len(container_info_list) == 1:
            return container_info_list[0]["PO_MSG"] == "No data found."

    def _is_container_no_error(self, container_info_list: List):
        if len(container_info_list) == 1:
            return (container_info_list[0]["PO_MSG"] or "").split(".")[0] == "Search condition error"


class NextRoundRoutingRule(BaseRoutingRule):
    name = "NEXT_ROUND"

    @classmethod
    def build_request_option(cls, container_no_list: List, sk) -> RequestOption:
        return RequestOption(
            rule_name=cls.name,
            method=RequestOption.METHOD_GET,
            url="https://eval.edi.hardcoretech.co/c/livez",
            meta={
                "container_no_list": container_no_list,
                "sk": sk,
            },
        )

    def handle(self, response):
        container_no_list = response.meta["container_no_list"]
        sk = response.meta["sk"]

        if len(container_no_list) <= MAX_PAGE_NUM:
            return

        container_no_list = container_no_list[MAX_PAGE_NUM:]

        yield ContainerRoutingRule.build_request_option(container_no_list=container_no_list, sk=sk)
