import scrapy
import json
import os
from scrapy.spiders import Spider
from scrapy.http import FormRequest
from scrapy.http import Request
from chainxy.items import ChainItem
from lxml import etree
from lxml import html

class AosomSpider(scrapy.Spider):
	name = 'aosom'
	domain = 'https://www.aosom.com/'

	def start_requests(self):
		yield scrapy.Request(url=self.domain, callback=self.parse_category)
		
	def parse_category(self, response):
		category_list = response.xpath('//div[@class="nav-container"]//div[@class="parentMenu"]//a/@rel').extract()
		for category in category_list:
			header = {
				"accept":"text/javascript, text/html, application/xml, text/xml, */*",
				"accept-encoding":"gzip, deflate, br",
				"content-type":"application/x-www-form-urlencoded; charset=UTF-8",
				"x-requested-with":"XMLHttpRequest"
			}
			formdata = {
				"amfpc_ajax_blocks":"left.reports.product.viewed"
			}
			yield scrapy.FormRequest(url=category, headers=header, method='post', formdata=formdata, callback=self.parse_product)

	def parse_product(self, response):
		try:
			data = response.body.replace('\u201d', '')
			data = json.loads(data)['listing']
			tree = etree.HTML(data)
			product_list = tree.xpath('//a[@class="product-image"]/@href')
			for product in product_list:
				yield scrapy.Request(url=product, callback=self.parse_page)

			try:
				pagenation = tree.xpath('//li[@class="pager-last"]//a/@href')[0]
				if pagenation:
					pagenation += '&isLayerAjax=1'
					header = {
						"accept":"text/javascript, text/html, application/xml, text/xml, */*",
						"accept-encoding":"gzip, deflate, sdch, br",
						"x-requested-with":"XMLHttpRequest"
					}
					yield scrapy.Request(url=pagenation, method='get', headers=header, callback=self.parse_product)
			except:
				pass
		except:
			pass

	def parse_page(self, response):
		try:
			item = ChainItem()
			item['Name'] = self.validate(response.xpath('//div[contains(@class, "product-shop")]//h1[@itemprop="name"]/text()').extract_first())
			item['Code'] = self.validate(response.xpath('//div[contains(@class, "product-shop")]//div[@class="product_sku"]//span[@class="sku"]/text()').extract_first())
			item['Price'] = self.validate(response.xpath('//div[contains(@class, "product-shop")]//div[@class="price-box"]//span[@class="price"]/text()').extract_first())
			status = response.xpath('//div[contains(@class, "product-shop")]//p[@class="availability in-stock"]//span/@class').extract_first()
			if 'checked' in status.lower():
				item['Status'] = 'True'
			else:
				item['Status'] = 'False'
			item['Description'] = self.str_concat(response.xpath('//div[contains(@class, "product-shop")]//div[@itemprop="description"]//text()').extract(), ', ')
			yield item
		except:
			pass


	def validate(self, item):
		try:
			return item.strip().replace('\u2013', '')
		except:
			return ''

	def str_concat(self, items, unit):
		tmp = ''
		for item in items[:-1]:
			if self.validate(item) != '':
				tmp += self.validate(item) + unit
		tmp += self.validate(items[-1])
		return tmp