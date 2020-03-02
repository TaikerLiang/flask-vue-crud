import re
from typing import List, Dict

import scrapy
from scrapy import Request
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


from crawler.core_carrier.base_spiders import BaseCarrierSpider
from crawler.core_carrier.exceptions import (
    LoadWebsiteTimeOutError, CarrierResponseFormatError, CarrierInvalidMblNoError)
from crawler.core_carrier.items import ContainerItem, ContainerStatusItem, LocationItem, MblItem, DebugItem
from crawler.extractors.table_cell_extractors import FirstTextTdExtractor
from crawler.extractors.table_extractors import BaseTableLocator, HeaderMismatchError, TableExtractor

URL = 'https://www.msc.com'


class CarrierMscuSpider(BaseCarrierSpider):
    name = 'carrier_mscu'

    def start(self):
        yield DebugItem(info='start')

        driver = MscuCarrierChromeDriver()

        for item in self.start_crawl(driver):
            yield item

        driver.close()

    def start_crawl(self, driver):
        driver.search_mbl_no(mbl_no=self.mbl_no)

        response_text = driver.get_body_text()
        response = scrapy.Selector(text=response_text)

        self._check_mbl_no(response=response)

        extractor = Extractor()

        place_of_deliv_set = set()
        container_selector_map_list = extractor.locate_container_selector(response=response)
        for container_selector_map in container_selector_map_list:
            container_no = extractor.extract_container_no(container_selector_map)

            yield ContainerItem(
                container_key=container_no,
                container_no=container_no,
            )

            container_status_list = extractor.extract_container_status_list(container_selector_map)
            for container_status in container_status_list:
                yield ContainerStatusItem(
                    container_key=container_no,
                    description=container_status['description'],
                    local_date_time=container_status['local_date_time'],
                    location=LocationItem(name=container_status['location']),
                    vessel=container_status['vessel'] or None,
                    voyage=container_status['voyage'] or None,
                    est_or_actual=container_status['est_or_actual'],
                )

            place_of_deliv = extractor.extract_place_of_deliv(container_selector_map)
            place_of_deliv_set.add(place_of_deliv)

        if not place_of_deliv_set:
            place_of_deliv = None
        elif len(place_of_deliv_set) == 1:
            place_of_deliv = list(place_of_deliv_set)[0] or None
        else:
            raise CarrierResponseFormatError(reason=f'Different place_of_deliv: `{place_of_deliv_set}`')

        mbl_no = extractor.extract_mbl_no(response=response)
        main_info = extractor.extract_main_info(response=response)
        latest_update = extractor.extract_latest_update(response=response)

        yield MblItem(
            mbl_no=mbl_no,
            pol=LocationItem(name=main_info['pol']),
            pod=LocationItem(name=main_info['pod']),
            etd=main_info['etd'],
            vessel=main_info['vessel'],
            place_of_deliv=LocationItem(name=place_of_deliv),
            latest_update=latest_update,
        )

    @staticmethod
    def _check_mbl_no(response: scrapy.Selector):
        error_message = response.css('div#ctl00_ctl00_plcMain_plcMain_pnlTrackingResults > h3::text').get()
        if error_message == 'No matching tracking information. Please try again.':
            raise CarrierInvalidMblNoError()


class Extractor:

    def __init__(self):
        self._mbl_no_pattern = re.compile(r'^Bill of lading: (?P<mbl_no>\S+) ([(]\d+ containers?[)])?$')
        self._container_no_pattern = re.compile(r'^Container: (?P<container_no>\S+)$')
        self._latest_update_pattern = re.compile(r'^Tracking results provided by MSC on (?P<latest_update>.+)$')

    def extract_mbl_no(self, response: scrapy.Selector):
        mbl_no_text = response.css('a#ctl00_ctl00_plcMain_plcMain_rptBOL_ctl00_hlkBOLToggle::text').get()

        if not mbl_no_text:
            return None

        return self._parse_mbl_no(mbl_no_text)

    def _parse_mbl_no(self, mbl_no_text: str):
        """
        Sample Text:
            `Bill of lading: MEDUN4194175 (1 container)`
            `Bill of lading: MEDUH3870035 `
        """
        m = self._mbl_no_pattern.match(mbl_no_text)
        if not m:
            raise CarrierResponseFormatError(reason=f'Unknown mbl no format: `{mbl_no_text}`')

        return m.group('mbl_no')

    @staticmethod
    def extract_main_info(response: scrapy.Selector):
        main_outer = response.css('div#ctl00_ctl00_plcMain_plcMain_rptBOL_ctl00_pnlBOLContent')
        error_message = 'Can not find main information frame by css `div#ctl00_ctl00_plcMain_plcMain_rptBOL_ctl00' \
                        '_pnlBOLContent`'
        if not main_outer:
            raise CarrierResponseFormatError(reason=error_message)

        table_selector = main_outer.xpath('./table[@class="resultTable singleRowTable"]')
        if not table_selector:
            return {
                'pol': None,
                'pod': None,
                'etd': None,
                'vessel': None,
            }

        table_locator = MainInfoTableLocator()
        table_locator.parse(table=table_selector)
        table_extractor = TableExtractor(table_locator=table_locator)
        td_extractor = FirstTextTdExtractor(css_query='span::text')

        return {
            'pol': table_extractor.extract_cell(top='Port of load', left=None, extractor=td_extractor),
            'pod': table_extractor.extract_cell(top='Port of discharge', left=None, extractor=td_extractor),
            'etd': table_extractor.extract_cell(top='Departure date', left=None, extractor=td_extractor),
            'vessel': table_extractor.extract_cell(top='Vessel', left=None, extractor=td_extractor),
        }

    @staticmethod
    def locate_container_selector(response) -> List[Dict]:
        container_content_list = response.css('dl.containerAccordion dd')
        map_list = []

        for container_content in container_content_list:
            container_no_bar = container_content.css('a.containerToggle')
            if not container_no_bar:
                raise CarrierResponseFormatError(reason='Can not find container_no_bar !!!')

            container_stats_table = container_content.css('table.containerStats')
            if not container_stats_table:
                raise CarrierResponseFormatError(reason='Can not find container_stats_table !!!')

            movements_table = container_content.css('table.resultTable')
            if not movements_table:
                raise CarrierResponseFormatError(reason='Can not find movements_table !!!')

            map_list.append({
                'container_no_bar': container_no_bar,
                'container_stats_table': container_stats_table,
                'movements_table': movements_table,
            })

        return map_list

    def extract_container_no(self, container_selector_map: Dict[str, scrapy.Selector]):
        container_no_bar = container_selector_map['container_no_bar']

        container_no_text = container_no_bar.css('::text').get()

        return self._parse_container_no(container_no_text)

    def _parse_container_no(self, container_no_text):
        """
        Sample Text:
            Container: GLDU7636572
        """
        m = self._container_no_pattern.match(container_no_text)

        if not m:
            raise CarrierResponseFormatError(reason=f'Unknown container no format: `{container_no_text}`')

        return m.group('container_no')

    @staticmethod
    def extract_place_of_deliv(container_selector_map: Dict[str, scrapy.Selector]):
        table_selector = container_selector_map['container_stats_table']

        table_locator = ContainerInfoTableLocator()
        table_locator.parse(table=table_selector)
        table_extractor = TableExtractor(table_locator=table_locator)
        td_extractor = FirstTextTdExtractor(css_query='span::text')

        return table_extractor.extract_cell(top='Shipped to', left=None, extractor=td_extractor)

    @staticmethod
    def extract_container_status_list(container_selector_map: Dict[str, scrapy.Selector]):
        table_selector = container_selector_map['movements_table']

        table_locator = ContainerStatusTableLocator()
        table_locator.parse(table=table_selector)
        table_extractor = TableExtractor(table_locator=table_locator)
        td_extractor = FirstTextTdExtractor(css_query='span::text')

        container_status_list = []
        for left in table_locator.iter_left_header():
            schedule_status = table_extractor.extract_cell(top=table_locator.STATUS_TOP, left=left)

            if schedule_status == 'past':
                est_or_actual = 'A'
            elif schedule_status == 'future':
                est_or_actual = 'E'
            else:
                raise CarrierResponseFormatError(reason=f'Unknown schedule_status: `{schedule_status}`')

            container_status_list.append({
                'location': table_extractor.extract_cell(top='Location', left=left, extractor=td_extractor),
                'local_date_time': table_extractor.extract_cell(top='Date', left=left, extractor=td_extractor),
                'description': table_extractor.extract_cell(top='Description', left=left, extractor=td_extractor),
                'vessel': table_extractor.extract_cell(top='Vessel', left=left, extractor=td_extractor),
                'voyage': table_extractor.extract_cell(top='Voyage', left=left, extractor=td_extractor),
                'est_or_actual': est_or_actual,
            })

        return container_status_list

    def extract_latest_update(self, response: scrapy.Selector):
        latest_update_message = response.css('div#ctl00_ctl00_plcMain_plcMain_pnlTrackingResults > p::text').get()
        return self._parse_latest_update(latest_update_message)

    def _parse_latest_update(self, latest_update_message: str):
        """
        Sample Text:
            Tracking results provided by MSC on 05.11.2019 at 10:50 W. Europe Standard Time
        """
        m = self._latest_update_pattern.match(latest_update_message)
        if not m:
            raise CarrierResponseFormatError(reason=f'Unknown latest update message format: `{latest_update_message}`')

        return m.group('latest_update').strip()


class MainInfoTableLocator(BaseTableLocator):
    """
    +-----------+-----------+-----+-----------+ <thead>      -+
    | Title A-1 | Title A-2 | ... | Title A-N | <tr> <th>     |
    +-----------+-----------+-----+-----------+ <tbody>       | A
    | Cell A-1  | Cell A-2  | ... | Cell A-N  | <tr> <td>     |
    +-----------+-----------+-----+-----------+ <thead>      -+
    | Title B-1 | Title B-2 | ... | Title B-N | <tr> <th>     |
    +-----------+-----------+-----+-----------+ <tbody>       | B
    | Cell B-1  | Cell B-2  | ... | Cell B-N  | <tr> <td>     |
    +-----------+-----------+-----+-----------+              -+
    """

    def __init__(self):
        self._td_map = {}  # top_header: td

    def parse(self, table: scrapy.Selector):
        thead_list = table.css('thead')
        tbody_list = table.css('tbody')

        for thead_index, thead in enumerate(thead_list):
            tbody_index = thead_index
            tbody = tbody_list[tbody_index]

            th_list = thead.css('tr th')
            td_list = tbody.css('tr td')

            for th_index, th in enumerate(th_list):
                td_index = th_index
                td = td_list[td_index]

                top = self._extract_top(th=th)
                self._td_map[top] = td

    @staticmethod
    def _extract_top(th):
        th_text = th.css('::text').get()
        return th_text.strip() if isinstance(th_text, str) else ''

    def get_cell(self, top, left) -> scrapy.Selector:
        assert left is None
        try:
            return self._td_map[top]
        except (KeyError, IndexError) as err:
            raise HeaderMismatchError(repr(err))

    def has_header(self, top=None, left=None) -> bool:
        return (top in self._td_map) and (left is None)


class ContainerInfoTableLocator(BaseTableLocator):
    """
    +-----------+-----------+-----+-----------+ <tbody>      -+
    | Title A-1 | Title A-2 | ... | Title A-N | <tr> <th>     |
    +-----------+-----------+-----+-----------+               | A
    | Cell A-1  | Cell A-2  | ... | Cell A-N  | <tr> <td>     |
    +-----------+-----------+-----+-----------+              -+
    | Title B-1 | Title B-2 | ... | Title B-N | <tr> <th>     |
    +-----------+-----------+-----+-----------+               | B
    | Cell B-1  | Cell B-2  | ... | Cell B-N  | <tr> <td>     |
    +-----------+-----------+-----+-----------+ <\tbody>     -+
    """

    def __init__(self):
        self._td_map = {}  # top_header: td

    def parse(self, table: scrapy.Selector):
        th_row_list = table.xpath('.//th/parent::tr')
        td_row_list = table.xpath('.//td/parent::tr')

        for th_row_index, th_row in enumerate(th_row_list):
            td_row_index = th_row_index
            td_row = td_row_list[td_row_index]

            th_list = th_row.css('th')
            td_list = td_row.css('td')

            for th_index, th in enumerate(th_list):
                td_index = th_index
                td = td_list[td_index]

                top = self._extract_top(th=th)
                self._td_map[top] = td

    @staticmethod
    def _extract_top(th):
        th_text = th.css('::text').get()
        return th_text.strip() if isinstance(th_text, str) else ''

    def get_cell(self, top, left) -> scrapy.Selector:
        assert left is None
        try:
            return self._td_map[top]
        except (KeyError, IndexError) as err:
            raise HeaderMismatchError(repr(err))

    def has_header(self, top=None, left=None) -> bool:
        return (top in self._td_map) and (left is None)


class ContainerStatusTableLocator(BaseTableLocator):

    STATUS_TOP = 'STATUS'

    def __init__(self):
        self._td_map = {}  # top_header: [td, ...]
        self._data_len = 0

    def parse(self, table: scrapy.Selector):
        th_list = table.css('thead th')
        data_tr_list = table.css('tbody tr')

        for th_index, th in enumerate(th_list):
            top_header = self._extract_top_header(th=th)
            self._td_map[top_header] = []

            data_index = th_index
            for data_tr in data_tr_list:
                data_td = data_tr.css('td')[data_index]
                self._td_map[top_header].append(data_td)

        tr_class_name_list = [data_tr.css('::attr(class)').get() for data_tr in data_tr_list]
        status_td_list = [
            scrapy.Selector(text=f'<td>{tr_class_name}</td>')
            for tr_class_name in tr_class_name_list
        ]
        self._td_map[self.STATUS_TOP] = status_td_list

        self._data_len = len(data_tr_list)

    @staticmethod
    def _extract_top_header(th):
        top_header = th.css('::text').get()
        return top_header.strip() if isinstance(top_header, str) else ''

    def get_cell(self, top, left) -> scrapy.Selector:
        try:
            return self._td_map[top][left]
        except (KeyError, IndexError) as err:
            raise HeaderMismatchError(repr(err))

    def has_header(self, top=None, left=None) -> bool:
        return (top in self._td_map) and (left is None)

    def iter_left_header(self):
        for i in range(self._data_len):
            yield i


class MscuCarrierChromeDriver:

    def __init__(self):
        prefs = {
            'profile.default_content_setting_values': {'images': 2},
        }

        options = webdriver.ChromeOptions()
        options.add_experimental_option('prefs', prefs)
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-extensions')
        options.add_argument('--headless')
        options.add_argument('window-size=1024x768')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-infobars')

        self._chrome_driver = webdriver.Chrome(chrome_options=options)

    def search_mbl_no(self, mbl_no):
        track_url = f'{URL}/track-a-shipment?agencyPath=twn'
        self._chrome_driver.get(url=track_url)

        search_bar_css_query = 'input#ctl00_ctl00_plcMain_plcMain_TrackSearch_txtBolSearch_TextField'
        search_bar_locator = (By.CSS_SELECTOR, search_bar_css_query)

        search_button_css_query = 'a#ctl00_ctl00_plcMain_plcMain_TrackSearch_hlkSearch'
        search_button_locator = (By.CSS_SELECTOR, search_button_css_query)

        try:
            WebDriverWait(self._chrome_driver, 10).until(EC.presence_of_element_located(search_bar_locator))
            WebDriverWait(self._chrome_driver, 10).until(EC.element_to_be_clickable(search_button_locator))
        except TimeoutException:
            raise LoadWebsiteTimeOutError()

        search_bar = self._chrome_driver.find_element_by_css_selector(search_bar_css_query)
        search_button = self._chrome_driver.find_element_by_css_selector(search_button_css_query)
        search_bar.send_keys(mbl_no)

        pop_up_reject_btn_locator = (By.CSS_SELECTOR, 'a#ctl00_ctl00_ucNewsetterSignupPopup_btnReject')
        if self._check_element_clickable(pop_up_reject_btn_locator):
            pop_up_reject_btn = self._chrome_driver.find_element(pop_up_reject_btn_locator)
            pop_up_reject_btn.click()

        search_button.click()

    def get_body_text(self):
        mbl_no_locator = (By.CSS_SELECTOR, 'div#ctl00_ctl00_plcMain_plcMain_pnlTrackingResults')

        try:
            WebDriverWait(self._chrome_driver, 10).until(EC.presence_of_element_located(mbl_no_locator))
        except TimeoutException:
            raise LoadWebsiteTimeOutError()

        body = self._chrome_driver.find_element_by_css_selector('body')
        body_text = body.get_attribute('outerHTML')

        return body_text

    def close(self):
        self._chrome_driver.close()

    def _check_element_clickable(self, locator):
        try:
            return bool(EC.element_to_be_clickable(locator)(self._chrome_driver))
        except NoSuchElementException:
            return False
