import abc
from pathlib import Path

import scrapy

from crawler.core.base_new import CLOSESPIDER_TIMEOUT, SEARCH_TYPE_AWB
from crawler.core_air.middlewares_new import AirSpiderMiddleware
from crawler.core_air.pipelines_new import AirItemPipeline, AirMultiItemsPipeline
from crawler.core_air.request_helpers_new import RequestOption
from crawler.general.savers import FileSaver, NullSaver
from crawler.utils.local_files.local_file_helpers import (
    LOCAL_PING_HTML,
    build_local_file_uri,
)

AIR_DEFAULT_SPIDER_MIDDLEWARES = {
    AirSpiderMiddleware.get_setting_name(): 900,
}

AIR_DEFAULT_ITEM_PIPELINES = {
    AirItemPipeline.get_setting_name(): 900,
}

AIR_DEFAULT_SETTINGS = {
    "SPIDER_MIDDLEWARES": {
        **AIR_DEFAULT_SPIDER_MIDDLEWARES,
    },
    "ITEM_PIPELINES": {
        **AIR_DEFAULT_ITEM_PIPELINES,
    },
}


class BaseAirSpider(scrapy.Spider):
    custom_settings = {
        "CLOSESPIDER_TIMEOUT": CLOSESPIDER_TIMEOUT,
        **AIR_DEFAULT_SETTINGS,
    }

    def __init__(self, name=None, **kwargs):
        super().__init__(name=name, **kwargs)

        self.request_args = kwargs

        self.task_id = kwargs["task_id"]
        self.mawb_no = kwargs["mawb_no"]
        self.search_type = SEARCH_TYPE_AWB

        to_save = "save" in kwargs
        self._saver = self._prepare_saver(to_save=to_save)

        self._error = False

    def start_requests(self):
        url = build_local_file_uri(local_file=LOCAL_PING_HTML)
        yield scrapy.Request(url=url, callback=self._parse_start)

    def _parse_start(self, response):
        for r in self.start():
            yield r

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def _build_request_by(self, option: RequestOption):
        pass

    def _prepare_saver(self, to_save: bool):
        if not to_save:
            return NullSaver()

        save_folder = Path(__file__).parent.parent.parent.parent / "_save_pages" / f"[{self.name}] {self.mawb_no}"

        return FileSaver(folder_path=save_folder, logger=self.logger)

    def has_error(self):
        return self._error

    def mark_error(self):
        self._error = True


# ---------------------------------------------------------------------------------------------------------------------


AIR_MULTI_ITEM_PIPELINES = {
    AirMultiItemsPipeline.get_setting_name(): 900,
}


class BaseMultiAirSpider(scrapy.Spider):

    custom_settings = {
        "CLOSESPIDER_TIMEOUT": CLOSESPIDER_TIMEOUT,
        "SPIDER_MIDDLEWARES": {
            **AIR_DEFAULT_SPIDER_MIDDLEWARES,
        },
        "ITEM_PIPELINES": {
            **AIR_MULTI_ITEM_PIPELINES,
        },
    }

    def __init__(self, name=None, **kwargs):
        super().__init__(name=name, **kwargs)

        self.request_args = kwargs

        self.task_ids = [task_id.strip() for task_id in kwargs["task_ids"].split(",")]
        self.mawb_nos = [mawb_no.strip() for mawb_no in kwargs["mawb_nos"].split(",")]
        self.mno_tid_map = {}  # mawb_no: [task_ids]
        for m_no, t_id in zip(self.mawb_nos, self.task_ids):
            self.mno_tid_map.setdefault(m_no, [])
            self.mno_tid_map[m_no].append(t_id)

        self.search_type = SEARCH_TYPE_AWB

        to_save = "save" in kwargs
        self._saver = self._prepare_saver(to_save=to_save)

        self._error = False

    def start_requests(self):
        # main entry point of scrapy
        url = build_local_file_uri(local_file=LOCAL_PING_HTML)
        yield scrapy.Request(url=url, callback=self._parse_start)

    def _parse_start(self, response):
        for r in self.start():
            yield r

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def _build_request_by(self, option: RequestOption):
        pass

    def _prepare_saver(self, to_save: bool):
        if not to_save:
            return NullSaver()

        save_folder = Path(__file__).parent.parent.parent.parent / "_save_pages" / f"[{self.name}] {self.mawb_nos}"

        return FileSaver(folder_path=save_folder, logger=self.logger)

    def has_error(self):
        return self._error

    def mark_error(self):
        self._error = True
