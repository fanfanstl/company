#!/usr/bin/python
# -*- coding: utf-8 -*-

## zara抓取程序，需要输入版本号 scrapy crawl zara -a taskId=1

import scrapy
import re
import json
import urlparse
import base64
import time
import copy
import common
import sys
import traceback
import logging
import pdb
import urllib
import hashlib
import os

from lib.common import Common
from scrapy import log
from goods.items import ProductInfo
from goods.items import SkuInfo
from goods.items import ImageInfo
from goods.items import UrlInfo
from goods.items import logInfo
from goods.items import ProxyInfo
from goods.items import SkuListInfo
from scrapy.utils.project import get_project_settings

settings = get_project_settings()
IMAGES_STORE = settings.get("IMAGES_STORE")


class baseSpider(scrapy.Spider):
    source_currency = "CNY"
    debug = "true"
    taskId = -1
    taskType = ''
    commonLib = False
    env_type = "offline"

    item_set = set([])
    parsePage = 'call_url'
    RETRY_TIMES = -5

    MAX_RETRY = 3
    MAX_RETRY_TOTAL = 1000
    _retryItemMap = {}
    _retryTimes = 0
    requestPriority = -10
    extra_urls = []

    # 扩展属性
    errorLogCount = 0



    # 自己添加代码
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        absPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(absPath, "log/currentLog.txt")
        with open(path, 'w') as f:
            f.truncate()
        spider = cls(*args, **kwargs)
        spider._set_crawler(crawler)
        return spider

    def start_requests(self):
        product_info = {}
        cookiejar = 1
        if self.taskType == 'spider_update' or self.taskType == 'special_spider':
            actualCnt = 1
            expectCnt = 1
            product_info['top_bar'] = 'new_spider'
            product_info['category_name'] = 'new_spider'
            product_info['sale'] = False
            sourceUrlList = json.loads(self.sourceUrls)

            for url in sourceUrlList:
                sale = False
                if "#sale" in url:
                    sale = True
                url = url.replace(",#sale", "").replace("#sale", "")

                product_info['sale'] = sale
                product_info['product_url'] = url
                request = scrapy.Request(url, callback=self.parse_product_detail)
                request.meta['product_info'] = copy.deepcopy(product_info)
                request.meta['retry_times'] = -10
                request.meta['method'] = sale
                request.dont_filter = True
                request.meta['cookiejar'] = cookiejar
                yield request
                cookiejar = cookiejar + 1
        else:
            for request_url in self.start_urls:
                request = scrapy.Request(request_url, callback=self.call_url)
                product_info['product_url'] = request_url
                request.meta['product_info'] = copy.deepcopy(product_info)
                request.meta['parsePage'] = self.parsePage
                request.meta['retry_times'] = -10
                request.dont_filter = True
                request.meta['cookiejar'] = cookiejar
                yield request
                cookiejar = cookiejar + 1

    def get_source_url(self, taskId):
        logging.info('get_task_info %s' % taskId)
        url = '/api/task/getTaskById'
        postData = {
            'taskId': taskId,
        }
        ret = self.commonLib.http_post(url, postData)
        retData = json.loads(ret)
        if retData['errno'] != 0 or not retData['data']:
            logging.warning("getTaskById failed and ret is [%s]" % (ret))
        else:
            taskInfo = retData['data']
            taskExtra = json.loads(taskInfo['extra'])
            if taskExtra.get('sourceUrlList', ''):
                self.extra_urls.extend(taskExtra['sourceUrlList'].split('\n'))

    def retry_url(self, product_info):
        url = product_info['product_url']
        parsePage = product_info['parsePage']
        self._retryTimes = self._retryTimes + 1
        self._retryItemMap[url] = self._retryItemMap.get(url, 0) + 1
        logging.warning("get_product_info failed retry to crawl item of [%s] in task [%s] , retry time is [%s]" % (
        url, self.taskId, self._retryItemMap[url]))

        if self._retryTimes >= self.MAX_RETRY_TOTAL:
            raise ValueError("spider beyond max total retry [%s]" % (url))

        if self._retryItemMap[url] <= self.MAX_RETRY:
            itemInfoList = []
            urlInfo = {
                "itemType": common.TYPE_URL,
                "item": url,
                "product_info": copy.deepcopy(product_info),
                "parsePage": parsePage,
                "dont_filter": True
            }
            itemInfoList.append(urlInfo)
            return itemInfoList
        else:
            raise ValueError("url is beyond max retry [%s]" % (url))

    def parse(self, response):
        logging.info('parse of [%s]', response.meta)

    def get_product_list(self, response):
        logging.info("get_product_list of url %s ", response.url)
        ## 打折
        itemInfoList = []
        product_info = response.meta.get("product_info")
        return itemInfoList

    def parse_product_detail(self, response):
        logging.info("parse new parse_product_detail  url is [%s]" % (response.url))
        itemInfoList = []

        # return
        method = 'get_product_info'
        response.meta['parsePage'] = method
        return self.call_url(response)

    def get_product_info(self, response):
        logging.info("parse product_info url is [%s]" % (response.url))

        itemInfoList = []
        product_info = response.meta.get("product_info")
        return itemInfoList

    def get_text_list(self, response, xpath, urljoin=False):
        infoList = []
        for option in response.xpath(xpath):
            option = option.extract().strip()
            if option:
                if urljoin == True:
                    option = response.urljoin(option)
                infoList.append(option)
        return infoList

    def spider_init(self):
        self.commonLib = Common()
        self.env_type = self.commonLib.get_env()
        if self.env_type == "online":
            self.debug = ""
        logging.info("task id is [%s] get debug is  [%s] , env_type is [%s]", self.taskId, self.debug, self.env_type)

    def call_url(self, response):
        # logging.info('call_url of [%s],meta is [%s]',response.url,response.meta)
        try:
            parsePage = response.meta['parsePage']
            expectCnt = 1
            actualCnt = 0
            urlStatus = common.STATUS_DONE
            itemInfoList = getattr(self, parsePage)(response)
            if not itemInfoList:
                return
            for urlInfo in itemInfoList:
                # logging.info('get urlInfo is [%s]',urlInfo)
                itemType = urlInfo.get("itemType")
                cookies = urlInfo.get("cookies", None)
                product_info = copy.deepcopy(urlInfo.get("product_info"))
                cookiejar = ''
                if product_info and product_info.get('cookiejar', ''):
                    cookiejar = product_info.get('cookiejar', '')
                if itemType == common.TYPE_URL:
                    dont_filter = urlInfo.get("dont_filter", False)
                    request = scrapy.Request(urlInfo['item'], cookies=cookies, dont_filter=dont_filter,
                                             callback=self.call_url)
                    request.meta['product_info'] = product_info
                    request.meta['parsePage'] = urlInfo.get("parsePage")
                    request.meta['retry_times'] = self.RETRY_TIMES
                    if cookiejar:
                        request.meta['cookiejar'] = cookiejar
                    if product_info and product_info.get('dont_filter') == True:
                        request.dont_filter = True
                    if product_info and product_info.get('priority'):
                        request.priority = product_info.get('priority')
                    # if product_info and product_info.get('proxy'):
                    #     request.meta['proxy'] = product_info.get('proxy')
                    yield request

                    if self.debug:
                        logging.info("in debug modal")
                        expectCnt = 1
                        break
                elif itemType == common.TYPE_ITEM:
                    product = ProductInfo()
                    for key, value in urlInfo['item'].items():
                        product[key] = value
                    yield product
                elif itemType == common.TYPE_SKU:
                    sku = SkuInfo()
                    for key, value in urlInfo['item'].items():
                        sku[key] = value
                    yield sku
                elif itemType == common.TYPE_SKULIST:
                    batchSku = SkuListInfo()
                    batchSku['itemType'] = common.TYPE_SKULIST
                    batchSku['sourceWebsite'] = urlInfo['item']['sourceWebsite']
                    batchSku['skuList'] = copy.deepcopy(urlInfo['item']['skuList'])
                    yield batchSku
                elif itemType == common.TYPE_SKU_STOCK_LIST:
                    batchSku = SkuListInfo()
                    batchSku['itemType'] = common.TYPE_SKU_STOCK_LIST
                    batchSku['sourceWebsite'] = urlInfo['item']['sourceWebsite']
                    batchSku['skuList'] = copy.deepcopy(urlInfo['item']['skuList'])
                    yield batchSku
                elif itemType == common.TYPE_PROXY:
                    proxy = ProxyInfo()
                    for key, value in urlInfo['item'].items():
                        proxy[key] = value
                    yield proxy
                elif itemType == common.TYPE_PIC:
                    image = ImageInfo()
                    image['itemType'] = common.TYPE_PIC
                    image['image_urls'] = urlInfo['item']
                    yield image
                elif itemType == common.TYPE_REQUEST:
                    request = urlInfo['item']
                    request.callback = self.call_url
                    request.meta['product_info'] = product_info
                    request.meta['parsePage'] = urlInfo.get("parsePage")
                    request.meta['retry_times'] = self.RETRY_TIMES
                    # print "------request call_url is " , request.callback
                    if cookiejar:
                        request.meta['cookiejar'] = cookiejar
                    yield request
                    # meta = response.meta
                    # depth = meta['depth']
                    # timestamp = "%.6f" % time.time()
                    # timestamp = timestamp.split(".")[-1]
                    # filename = "%s/%s/%s_%s_%s.html" % (self.name, str(self.taskId), depth, parsePage, timestamp)
                    # self.commonLib.write_file(filename, response.body)
        except Exception as e:
            urlStatus = common.STATUS_FAIL
            msgStr = json.dumps(traceback.format_exc())
            logging.warning(msgStr)

            # 自己添加功能
            absPath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(absPath, "log/currentLog.txt")
            msgStrList = msgStr.split("\\n")
            with open(path, 'a') as f:
                self.errorLogCount += 1
                f.write(("*" * 20 + "第%d条" + "*" * 20 + "\n") % self.errorLogCount)
                for msgS in msgStrList:
                    f.write(msgS)
                    f.write('\n')
                f.write("\n\n\n\n")
            pdb.set_trace()


            yield common.addLog(msgStr, self.taskId, common.LOG_FATAL, response.url, self.name)
        finally:
            yield common.addUrl(response.url, self.taskId, '', common.LEVEL_CATEGORY1, -1, -1, urlStatus)

    def getSkuSourceSaleTime(self, sourceSkuId, type, value):
        logging.info('getSkuSourceSaleTime')
        logging.info('sku %s, type %s, value %s' % (sourceSkuId, type, value))
        sourceSaleTime = ''
        returnMap = {}
        # 待验证正则
        # \d{1,2}[\u6708|.]\d{0,2}[\u65e5|\u53f7]{0,1}
        sourceSaleTimeReList = [
            # ur'\d{1,2}\u6708\d{0,2}[\u65e5|\u53f7]{0,1}',
            ur'\d{1,2}[\u6708|\.]{1}\d{0,2}[\u65e5|\u53f7]{0,1}',
            ur'[\d|\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]{0,2}\u6708[\u521d|\u5e95|\u4e0a\u65ec|\u4e2d\u65ec|\u4e0b\u65ec]{1,2}',
        ]
        monthRe = ur'[\u5e95\u521d\u65ec]{1}'
        sourceSaleTime = ''
        for sourceSaleTimeRe in sourceSaleTimeReList:
            sourceSaleTime = re.findall(sourceSaleTimeRe, value.decode('utf8'))
            logging.info('sourceSkuId %s , sourceSaleTime %s' % (sourceSkuId, sourceSaleTime))
            if len(sourceSaleTime) == 1 and ('月' in sourceSaleTime[0] or '.' in sourceSaleTime[0]) and not re.findall(
                    monthRe, value.decode('utf8')):
                # sourceSaleTime = sourceSaleTime[0]
                # value = value.split(sourceSaleTime[0])[0]
                # returnMap['sourceSaleTime'] = self.str_replace(sourceSaleTime)
                # returnMap['value'] = value
                # returnMap = self.getSkuSourceSaleTimeMap(sourceSaleTime)
                break
            elif len(sourceSaleTime) == 1 and '月' in sourceSaleTime[0] and re.match(monthRe, sourceSaleTime[0]):
                # returnMap = self.getSkuSourceSaleTimeMap(sourceSaleTime)
                break
        if sourceSaleTime:
            returnMap = self.getSkuSourceSaleTimeMap(sourceSaleTime[0], value)
        return returnMap

    def str_replace(self, strValue):
        strValue = strValue.replace('发货', '').replace('预售', '').replace(',', '').replace('，', '').replace('（',
                                                                                                          '').replace(
            '(', '').strip()
        return strValue

    def getSkuSourceSaleTimeMap(self, sourceSaleTimeOption, value):
        returnMap = {}
        sourceSaleTime = sourceSaleTimeOption
        value = value.split(sourceSaleTime)[0]
        returnMap['sourceSaleTime'] = self.str_replace(sourceSaleTime)
        returnMap['value'] = self.str_replace(value)
        return returnMap

    def downloadPic(self, picUrl):
        logging.info('downloadPic, picUrl %s' % (picUrl))
        fileName = hashlib.md5(picUrl).hexdigest() + '.jpg'
        filePath = IMAGES_STORE + "full/" + fileName
        if os.path.isfile(filePath):
            logging.info('picUrl %s, download done' % picUrl)
            ret = self.uploadPic(picUrl, filePath)
        else:
            try:
                result = urllib.urlretrieve(picUrl, filePath)
            except urllib.ContentTooShortError:
                logging.warning(
                    'retry, download fail,picUrl  %s, error msg %s' % (picUrl, urllib.ContentTooShortError.message))
                result = urllib.urlretrieve(picUrl, filePath)
            logging.info('downloadPic result is %s' % result[0])
            if os.path.isfile(result[0]):
                ret = self.uploadPic(picUrl, result[0])
            else:
                ret = self.uploadPic(picUrl, common.STATUS_FAIL)
        logging.info('uploadPic ret %s' % json.dumps(ret))
        return ret

    def uploadPic(self, picUrl, picPath):
        logging.info('uploadPic picUrl is %s, picPath %s' % (picUrl, picPath))
        url = '/api/spider/uploadPic'
        post_data = {
            'picUrl': picUrl,
            'picPath': picPath,
        }
        ret = self.commonLib.http_post(url, post_data)
        logging.info('uploadPic ret %s' % (ret))
        data = json.loads(ret)
        if data['errno'] != 0:
            logging.warning('upload pic Fail')
            return {}
        fkey = data['data']['picKey']
        qiniuUrl = 'https://pic.bbtkids.cn/%s' % fkey
        return {'fkey': fkey, 'qiniuUrl': qiniuUrl}

