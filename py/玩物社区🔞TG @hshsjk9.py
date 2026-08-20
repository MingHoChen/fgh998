"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '811_Final_Perfect_Fix_V2',
  lang: 'hipy'
})
"""

# -*- coding: utf-8 -*-
import re
import urllib.parse
import requests
import json
from base64 import b64encode
from base.spider import Spider as BaseSpider

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

class Spider(BaseSpider):
    def __init__(self, query_params=None, t4_api=None):
        super().__init__(query_params, t4_api)
        self.t4_api = t4_api
        self.host = 'https://wanwuu.com/'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Referer': self.host,
        }
        self.classes = [
            {"type_name": "国产SM", "type_id": "guochan-sm"},
            {"type_name": "日韩SM", "type_id": "rihan-sm"},
            {"type_name": "欧美SM", "type_id": "oumei-sm"},
            {"type_name": "直播回放", "type_id": "zhibo-huifang"}
        ]

    def getName(self): return "玩物社区"
    def init(self, extend=""): pass
    def isVideoFormat(self, url): return False
    def manualVideoCheck(self): return False
    def homeContent(self, filter): return {"class": self.classes}
    
    def homeVideoContent(self): 
        return self.categoryContent("guochan-sm", "1", False, {})

    def localProxy(self, params):
        img_url = params.get('url')
        if not img_url: return [404, "text/plain", "No URL"]
        try:
            res = requests.get(img_url, headers=self.headers, timeout=15, verify=False)
            data = res.content
            if data.startswith(b'\x89PNG'): return [200, "image/png", data]
            if data.startswith(b'\xff\xd8\xff'): return [200, "image/jpeg", data]
            if HAS_CRYPTO:
                key, iv = b"f5d965df75336270", b'97b60394abc2fbe1'
                cipher = AES.new(key, AES.MODE_CBC, iv)
                pt = cipher.decrypt(data)
                try: pt = unpad(pt, AES.block_size)
                except: pt = pt.rstrip(b'\x00')
                mime = "image/png" if pt.startswith(b'\x89PNG') else "image/jpeg"
                return [200, mime, pt]
            return [200, "image/jpeg", data]
        except: return [500, "text/plain", "Proxy Error"]

    def _get_proxy_url(self, img_url):
        if not img_url or not self.t4_api: return img_url
        connector = '&' if '?' in self.t4_api else '?'
        return f"{self.t4_api}{connector}url={urllib.parse.quote(img_url)}"

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}videos/{tid}/page/{pg}/"
        try:
            r = requests.get(url, headers=self.headers, timeout=10, verify=False)
            return self._page(self._parse_list(r.text), pg)
        except: return self._page([], pg)

    def _parse_list(self, html):
        videos = []
        pattern = r'class="video-item"\s+href="([^"]+)".*?data-src="([^"]+)"\s+alt="([^"]+)"'
        matches = re.findall(pattern, html, re.S)
        for href, img_url, title in matches:
            videos.append({
                "vod_id": self._abs(href), "vod_name": title.strip(),
                "vod_pic": self._get_proxy_url(img_url), "vod_remarks": "高清"
            })
        return videos

    def detailContent(self, ids):
        vid = ids[0]
        try:
            r = requests.get(vid, headers=self.headers, timeout=10, verify=False)
            html = r.text
            vod = {
                "vod_id": vid, "vod_name": "视频详情", "vod_pic": "",
                "vod_type": "", "vod_year": "", "vod_area": "大陆",
                "vod_remarks": "高清", "vod_actor": "未知", "vod_director": "未知",
                "vod_content": "暂无简介"
            }

            json_ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
            if json_ld:
                try:
                    data = json.loads(json_ld.group(1).strip())
                    vod["vod_name"] = data.get("name", vod["vod_name"])
                    vod["vod_pic"] = self._get_proxy_url(data.get("thumbnailUrl", ""))
                    vod["vod_content"] = data.get("description", "暂无简介").strip()
                    vod["vod_year"] = data.get("uploadDate", "")[:4]
                    if "keywords" in data:
                        vod["vod_type"] = data["keywords"].replace(",", " / ")
                except: pass

            play_url = vid
            embed_match = re.search(r'"embedUrl":\s*"([^"]+)"', html)
            if embed_match:
                embed_url = self._abs(embed_match.group(1).replace('\\', ''))
                r_e = requests.get(embed_url, headers=self.headers, timeout=10, verify=False)
                inner_s = re.search(r'<source\s+src="([^"]+)"', r_e.text)
                if inner_s: play_url = inner_s.group(1).replace('\\', '')

            vod["vod_play_from"] = "玩物社区"
            vod["vod_play_url"] = f"立即播放${play_url}"
            return {"list": [vod]}
        except: return {"list": []}

    def searchContent(self, key, quick, pg='1'):
        wd = urllib.parse.quote(key)
        url = f"{self.host}videos/search/{wd}/page/{pg}/"
        try:
            r = requests.get(url, headers=self.headers, timeout=10, verify=False)
            return self._page(self._parse_list(r.text), pg)
        except: return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 0, "url": id, "header": self.headers}

    def _abs(self, url): return urllib.parse.urljoin(self.host, url)
    def _page(self, videos, pg):
        return {"page": int(pg), "pagecount": int(pg)+1, "list": videos}