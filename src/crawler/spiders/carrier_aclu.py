import abc
import dataclasses
import re
from typing import List, Pattern, Match, Dict, Union

import scrapy

from crawler.core_carrier.base_spiders import BaseCarrierSpider
from crawler.core_carrier.exceptions import CarrierResponseFormatError, CarrierInvalidMblNoError
from crawler.core_carrier.rules import RuleManager, RoutingRequest, BaseRoutingRule
from crawler.core_carrier.items import BaseCarrierItem, ContainerItem, ContainerStatusItem, LocationItem
from crawler.extractors.selector_finder import CssQueryTextStartswithMatchRule, find_selector_from

ACLU_BASE_URL = 'http://www.aclcargo.com'


class CarrierAcluSpider(BaseCarrierSpider):
    name = 'carrier_aclu'

    def __init__(self, *args, **kwargs):
        super(CarrierAcluSpider, self).__init__(*args, **kwargs)

        rules = [
            SearchRoutingRule(),
            HistoryRoutingRule(),
        ]

        self._rule_manager = RuleManager(rules=rules)

    def start_requests(self):

        routing_request = SearchRoutingRule.build_routing_request(mbl_no=self.mbl_no)
        yield self._rule_manager.build_request_by(routing_request=routing_request)

    def parse(self, response):
        routing_rule = self._rule_manager.get_rule_by_response(response=response)

        save_name = routing_rule.get_save_name(response=response)
        self._saver.save(to=save_name, text=response.text)

        for result in routing_rule.handle(response=response):
            if isinstance(result, BaseCarrierItem):
                yield result
            elif isinstance(result, RoutingRequest):
                yield self._rule_manager.build_request_by(routing_request=result)
            else:
                raise RuntimeError()


# -------------------------------------------------------------------------------

class SearchRoutingRule(BaseRoutingRule):
    name = 'SEARCH'

    @classmethod
    def build_routing_request(cls, mbl_no: str) -> RoutingRequest:
        request = scrapy.Request(
            url=f'{ACLU_BASE_URL}/trackCargo.php?search_for={mbl_no}',
        )
        return RoutingRequest(request=request, rule_name=cls.name)

    def get_save_name(self, response) -> str:
        return f'{self.name}.html'

    def handle(self, response):
        self._check_mbl_no(response)

        container_infos = self._extract_container_infos(response=response)
        for container_info in container_infos:
            yield HistoryRoutingRule.build_routing_request(
                route=container_info['route'], container_no=container_info['container_no'])

    @staticmethod
    def _check_mbl_no(response):
        first_header_text = response.css('span.subheader::text').get()
        if first_header_text == 'An Error Occured:':
            raise CarrierInvalidMblNoError()

        # container no invalid
        h1_selectors = response.css('h1')
        title_rule = CssQueryTextStartswithMatchRule(css_query='::text', startswith='TRACK CARGO')
        track_title_selector = find_selector_from(selectors=h1_selectors, rule=title_rule)

        table = track_title_selector.xpath('./following-sibling::table//table//table')
        if not table:
            return

        tds = table.css('td')
        mbl_not_active_rule = CssQueryTextStartswithMatchRule(
            css_query='::text', startswith='Unit is no longer active, please contact ACL for additional information')
        mbl_not_active_td = find_selector_from(selectors=tds, rule=mbl_not_active_rule)
        if mbl_not_active_td:
            raise CarrierInvalidMblNoError()

    def _extract_container_infos(self, response: scrapy.Selector):
        detail_track_texts = response.css('input#DetailedTrack::attr(onclick)').getall()

        if not detail_track_texts:
            raise CarrierResponseFormatError('Can not found detail track button!!!')

        container_infos = []
        for detail_track_text in detail_track_texts:
            detail_tracking = self._parse_detail_tracking(detail_track_text=detail_track_text)
            container_infos.append(detail_tracking)

        return container_infos

    @staticmethod
    def _parse_detail_tracking(detail_track_text: str) -> Dict:
        pattern = re.compile(r"^getHistory[(]'(?P<route>.+Equino=(?P<container_no>[^&]+)[^']+)'[)];$")

        m = pattern.match(detail_track_text)
        if not m:
            raise CarrierResponseFormatError(reason='Detail track not match')

        return {
            'route': m.group('route'),
            'container_no': m.group('container_no'),
        }


# -------------------------------------------------------------------------------


@dataclasses.dataclass
class StatusInfo:
    description: str
    local_date_time: str
    location: str = ''
    vessel: str = ''


class HistoryRoutingRule(BaseRoutingRule):
    name = 'HISTORY'

    def __init__(self):
        self.parsers = [
            LoadedFullWithETAStatusParser(
                patt=re.compile(
                    r'^(?P<load_event>Loaded full on vessel (?P<vessel>.+)) for (?P<location>.+) On '
                    r'(?P<local_date_time1>\w{2}/\w{2}/\w{2} \w{2}:\w{2}) (?P<sail_event>which sailed on) '
                    r'(?P<local_date_time2>\w{2}/\w{2}/\w{2} \w{2}:\w{2})\. '
                    r'(?P<eta_event>The ETA at the port of Discharge will be) '
                    r'(?P<local_date_time3>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            LoadedFullWithETAStatusParser(
                patt=re.compile(
                    r'^(?P<load_event>Loaded full on vessel (?P<vessel>.+)) for (?P<location>.+) On '
                    r'(?P<local_date_time1>\w{2}/\w{2}/\w{2} \w{2}:\w{2}) (?P<sail_event>Sail Date) '
                    r'(?P<local_date_time2>\w{2}/\w{2}/\w{2} \w{2}:\w{2})\. '
                    r'(?P<eta_event>The ETA at the port of Discharge) -'
                    r'(?P<local_date_time3>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            LoadedFullStatusParser(
                patt=re.compile(
                    r'^(?P<load_event>Loaded full on vessel (?P<vessel>.+)) for (?P<location>.+) On '
                    r'(?P<local_date_time1>\w{2}/\w{2}/\w{2} \w{2}:\w{2}) (?P<sail_event>which sailed on) '
                    r'(?P<local_date_time2>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            LoadedFullStatusParser(
                patt=re.compile(
                    r'^(?P<load_event>Loaded full on vessel (?P<vessel>.+)) for (?P<location>.+) On '
                    r'(?P<local_date_time1>\w{2}/\w{2}/\w{2} \w{2}:\w{2}) (?P<sail_event>Sail Date) '
                    r'(?P<local_date_time2>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            VesselLocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Discharged from vessel (?P<vessel>.+) at (?P<location>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            VesselLocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Received for vessel (?P<vessel>.+) at (?P<location>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            VesselLocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Received from vessel (?P<vessel>.+) at (?P<location>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            VesselLocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Departed for (?P<location>.+) for vessel (?P<vessel>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            VesselLocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Departed from (?P<location>.+) from vessel (?P<vessel>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            LocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Departed empty for (?P<location>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            LocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Discharged empty at (?P<location>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            LocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Received empty at (?P<location>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            LocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Departed for (?P<location>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            LocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Departed from (?P<location>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            LocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Received at (?P<location>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            LocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Scaled in at (?P<location>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            LocationTimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Scaled out at ,(?P<location>.+)) On '
                    r'(?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            TimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Stripped at) On (?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
            TimeStatusParser(
                patt=re.compile(
                    r'^(?P<description>Stuffed at) On (?P<local_date_time>\w{2}/\w{2}/\w{2} \w{2}:\w{2})'
                ),
            ),
        ]

        self.status_transformer = StatusTransformer(parsers=self.parsers)

    @classmethod
    def build_routing_request(cls, route: str, container_no: str) -> RoutingRequest:
        request = scrapy.Request(
            url=f'{ACLU_BASE_URL}{route}',
        )
        request.meta['container_no'] = container_no
        return RoutingRequest(request=request, rule_name=cls.name)

    def get_save_name(self, response) -> str:
        container_no = response.meta['container_no']
        return f'{self.name}_{container_no}.html'

    def handle(self, response):
        container_no = self._extract_container_no(response=response)
        yield ContainerItem(
            container_key=container_no,
            container_no=container_no,
        )

        status_info_list = self._extract_status_info_list(response=response)
        for status_info in status_info_list:
            yield ContainerStatusItem(
                container_key=container_no,
                description=status_info.description,
                local_date_time=status_info.local_date_time,
                location=LocationItem(name=status_info.location or None),
                vessel=status_info.vessel or None,
            )

    def _extract_container_no(self, response: scrapy.Selector) -> str:
        container_no_text = response.css('span.subheader::text').get()

        if not container_no_text:
            raise CarrierResponseFormatError(reason='Container_no not found')

        return self._parse_container_no(container_no_text=container_no_text)

    @staticmethod
    def _parse_container_no(container_no_text: str) -> str:
        pattern = re.compile(r'^Detailed tracking for: (?P<container_no>\w+)$')

        m = pattern.match(container_no_text)
        if not m:
            raise CarrierResponseFormatError(reason='Container_no not match')

        return m.group('container_no')

    def _extract_status_info_list(self, response: scrapy.Selector) -> List[StatusInfo]:
        text_startswith_math_rule = CssQueryTextStartswithMatchRule(css_query='::text', startswith='var dataContent')
        status_text_selector = find_selector_from(selectors=response.css('script'), rule=text_startswith_math_rule)

        status_text = status_text_selector.css('::text').get()

        container_status_text_list = re.findall(r"'(?P<text>[^']+)'", status_text)
        if not container_status_text_list:
            CarrierResponseFormatError(reason='Container_status_list not found')

        container_status_list = []
        for status_text in container_status_text_list:
            status_text = ' '.join(status_text.split())  # replace special space char

            status_infos = self.status_transformer.transform(status_text=status_text)
            container_status_list.extend(status_infos)

        return container_status_list


# -------------------------------------------------------------------------------


class BaseStatusParser:

    @abc.abstractmethod
    def match(self, status_text: str) -> Union[Match, None]:
        pass

    @abc.abstractmethod
    def process(self, match_dict: Dict) -> List[StatusInfo]:
        pass


class StatusTransformer:

    def __init__(self, parsers: List[BaseStatusParser]):
        self.parsers = parsers

    def transform(self, status_text) -> List[StatusInfo]:
        for parser in self.parsers:
            m = parser.match(status_text=status_text)
            if m:
                return parser.process(match_dict=m.groupdict())

        raise CarrierResponseFormatError(status_text)


# -------------------------------------------------------------------------------


class TimeStatusParser(BaseStatusParser):

    def __init__(self, patt: Pattern):
        assert 'description' in patt.groupindex
        assert 'local_date_time' in patt.groupindex

        self.patt = patt

    def match(self, status_text: str) -> Union[Match, None]:
        return self.patt.match(status_text)

    def process(self, match_dict: Dict) -> List[StatusInfo]:
        return [
            StatusInfo(
                description=match_dict['description'],
                local_date_time=match_dict['local_date_time'],
            ),
        ]


class LocationTimeStatusParser(BaseStatusParser):

    def __init__(self, patt: Pattern):
        assert 'description' in patt.groupindex
        assert 'location' in patt.groupindex
        assert 'local_date_time' in patt.groupindex

        self.patt = patt

    def match(self, status_text: str) -> Union[Match, None]:
        return self.patt.match(status_text)

    def process(self, match_dict: Dict) -> List[StatusInfo]:
        return [
            StatusInfo(
                description=match_dict['description'],
                location=match_dict['location'],
                local_date_time=match_dict['local_date_time'],
            ),
        ]


class VesselLocationTimeStatusParser(BaseStatusParser):

    def __init__(self, patt: Pattern):
        assert 'description' in patt.groupindex
        assert 'vessel' in patt.groupindex
        assert 'location' in patt.groupindex
        assert 'local_date_time' in patt.groupindex

        self.patt = patt

    def match(self, status_text: str) -> Union[Match, None]:
        return self.patt.match(status_text)

    def process(self, match_dict: Dict) -> List[StatusInfo]:
        return [
            StatusInfo(
                description=match_dict['description'],
                vessel=match_dict['vessel'],
                location=match_dict['location'],
                local_date_time=match_dict['local_date_time'],
            ),
        ]


class LoadedFullWithETAStatusParser(BaseStatusParser):

    def __init__(self, patt: Pattern):
        assert 'load_event' in patt.groupindex
        assert 'vessel' in patt.groupindex
        assert 'location' in patt.groupindex
        assert 'local_date_time1' in patt.groupindex
        assert 'local_date_time2' in patt.groupindex
        assert 'local_date_time3' in patt.groupindex
        assert 'sail_event' in patt.groupindex
        assert 'eta_event' in patt.groupindex

        self.patt = patt

    def match(self, status_text: str) -> Union[Match, None]:
        return self.patt.match(status_text)

    def process(self, match_dict: Dict) -> List[StatusInfo]:
        return [
            StatusInfo(
                description=match_dict['load_event'],
                local_date_time=match_dict['local_date_time1'],
                vessel=match_dict['vessel'],
            ),
            StatusInfo(
                description=match_dict['sail_event'],
                local_date_time=match_dict['local_date_time2'],
                vessel=match_dict['vessel'],
            ),
            StatusInfo(
                description=match_dict['eta_event'],
                location=match_dict['location'],
                local_date_time=match_dict['local_date_time3'],
                vessel=match_dict['vessel'],
            ),
        ]


class LoadedFullStatusParser(BaseStatusParser):

    def __init__(self, patt: Pattern):
        assert 'load_event' in patt.groupindex
        assert 'vessel' in patt.groupindex
        assert 'location' in patt.groupindex
        assert 'local_date_time1' in patt.groupindex
        assert 'local_date_time2' in patt.groupindex
        assert 'sail_event' in patt.groupindex

        self.patt = patt

    def match(self, status_text: str) -> Union[Match, None]:
        return self.patt.match(status_text)

    def process(self, match_dict: Dict) -> List[StatusInfo]:
        return [
            StatusInfo(
                description=match_dict['load_event'],
                local_date_time=match_dict['local_date_time1'],
                vessel=match_dict['vessel'],
            ),
            StatusInfo(
                description=match_dict['sail_event'],
                local_date_time=match_dict['local_date_time2'],
                vessel=match_dict['vessel'],
            ),
        ]
