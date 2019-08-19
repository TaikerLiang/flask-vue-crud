# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class ExportFinalData(scrapy.Item):
    pass


class ExportErrorData(scrapy.Item):
    status = scrapy.Field()
    detail = scrapy.Field()


class LocationItem(scrapy.Item):
    name = scrapy.Field()
    un_lo_code = scrapy.Field()
    firms_code = scrapy.Field()


class MblItem(scrapy.Item):
    mbl_no = scrapy.Field()
    vessel = scrapy.Field()
    voyage = scrapy.Field()
    por = scrapy.Field(serializer=LocationItem)
    pol = scrapy.Field(serializer=LocationItem)
    pod = scrapy.Field(serializer=LocationItem)
    place_of_deliv = scrapy.Field(serializer=LocationItem)
    final_dest = scrapy.Field(serializer=LocationItem)
    por_etd = scrapy.Field()
    por_atd = scrapy.Field()
    pol_ata = scrapy.Field()
    etd = scrapy.Field()
    atd = scrapy.Field()
    eta = scrapy.Field()
    ata = scrapy.Field()
    bl_type = scrapy.Field()
    deliv_eta = scrapy.Field()
    deliv_ata = scrapy.Field()
    trans_eta = scrapy.Field()
    cargo_cutoff_date = scrapy.Field()
    surrendered_status = scrapy.Field()
    container_quantity = scrapy.Field()
    us_ams_status = scrapy.Field()
    ca_aci_status = scrapy.Field()
    eu_ens_status = scrapy.Field()
    cn_cams_status = scrapy.Field()
    ja_afr_status = scrapy.Field()
    freight_status = scrapy.Field()
    us_customs_status = scrapy.Field()
    us_customs_date = scrapy.Field()
    way_bill_status = scrapy.Field()
    way_bill_date = scrapy.Field()
    deliv_order = scrapy.Field()
    latest_update = scrapy.Field()
    firms_code = scrapy.Field()
    freight_date = scrapy.Field()


class VesselItem(scrapy.Item):
    vessel = scrapy.Field()
    voyage = scrapy.Field()
    pol = scrapy.Field(serializer=LocationItem)
    pod = scrapy.Field(serializer=LocationItem)
    etd = scrapy.Field()
    eta = scrapy.Field()
    atd = scrapy.Field()
    ata = scrapy.Field()
    discharge_date = scrapy.Field()
    shipping_date = scrapy.Field()
    row_no = scrapy.Field()
    sequence_no = scrapy.Field()

    @property
    def key(self):
        return self['vessel']


class ContainerItem(scrapy.Item):
    container_no = scrapy.Field()
    last_free_day = scrapy.Field()
    depot_last_free_day = scrapy.Field()
    empty_pickup_date = scrapy.Field()
    empty_return_date = scrapy.Field()
    full_pickup_date = scrapy.Field()
    full_return_date = scrapy.Field()
    ams_release = scrapy.Field()
    mt_location = scrapy.Field()
    det_free_time_exp_date = scrapy.Field()
    por_etd = scrapy.Field()
    pol_etd = scrapy.Field()
    final_dest_eta = scrapy.Field()
    ready_for_pick_up = scrapy.Field()

    @property
    def key(self):
        return self['container_no']


class ContainerStatusItem(scrapy.Item):
    container_no = scrapy.Field()
    description = scrapy.Field()
    timestamp = scrapy.Field()
    location = scrapy.Field(serializer=LocationItem)
    transport = scrapy.Field()
    est_or_actual = scrapy.Field()

    @property
    def key(self):
        return self['container_no']
