import scrapy


class BaseItem(scrapy.Item):
    pass


class ExportErrorData(BaseItem):
    task_id = scrapy.Field()
    search_no = scrapy.Field()
    search_type = scrapy.Field()  # SEARCH_TYPE_XXX in src/crawler/core/base.py
    status = scrapy.Field()
    detail = scrapy.Field()
    traceback_info = scrapy.Field()


class DataNotFoundItem(BaseItem):
    task_id = scrapy.Field()
    search_no = scrapy.Field()
    search_type = scrapy.Field()  # SEARCH_TYPE_XXX in src/crawler/core/base.py
    status = scrapy.Field()
    detail = scrapy.Field()
