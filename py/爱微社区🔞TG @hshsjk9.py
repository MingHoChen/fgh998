# -*- coding: utf-8 -*-
import sys
import re
import json
import requests
from urllib.parse import quote

try:
    from base.spider import Spider
except ImportError:
    from base.spider import Spider

HOST = 'https://bav52.cc'
HOSTS = ['https://bav52.cc', 'https://bav53.cc', 'https://bav62.cc', 'https://avjb.com']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
CATEGORIES = [
    {"type_id": "new", "type_name": "最新"},
    {"type_id": "f238838498ffcbbb9dec54cff3d68e1f", "type_name": "福利姬"},
    {"type_id": "c8ed8a54e38ed0c5276281131a5a128e", "type_name": "网红"},
    {"type_id": "d28b92e24cc1d6cb1e5e44c32f2c53bb", "type_name": "制服"},
    {"type_id": "79981faea06a7ee7c0f04fb66bb54663", "type_name": "丝袜"},
    {"type_id": "db7ad71b1af7e9f5a07a18aa1dc0daf0", "type_name": "御姐"},
    {"type_id": "8abae1aec219fe06cf74b24338093e74", "type_name": "高颜值"},
    {"type_id": "a686a94189bca9341082307e1ce07663", "type_name": "美女"},
    {"type_id": "9b39cf7137c40ff936512e0f34f7f472", "type_name": "尤物"},
    {"type_id": "239c00a652ca5330d6aaa4b49c2d724d", "type_name": "极品"},
    {"type_id": "9a0cd4bae997e3e887e537453eac235c", "type_name": "姐姐"},
    {"type_id": "b7d9f81d20aa9e44d1c129b9ba335fc4", "type_name": "成熟的女人"},
    {"type_id": "d5dda49a594b691685feaadb9d7d1352", "type_name": "已婚女人"},
    {"type_id": "32b531f1c1664ce095f938ed30543827", "type_name": "已婚妇女"},
    {"type_id": "e69d1bdaa72210b0c599fdcaab0bf2cd", "type_name": "性感"},
    {"type_id": "409463c53c9018e77e4293fef31cf4ab", "type_name": "私拍"},
    {"type_id": "920ff7821a4fb5775a40a8aace6fdfcb", "type_name": "裸舞"},
    {"type_id": "542e1afd76c7ea706511ef5f7ebf80fe", "type_name": "调教"},
    {"type_id": "ed33a738add85dea56df71cffc7be030", "type_name": "高潮"},
    {"type_id": "5c8163bf649cc7e5e4959f597f152755", "type_name": "自慰"},
    {"type_id": "ae5655f7352b5ce0e7a161307a5c1b35", "type_name": "口交"},
    {"type_id": "b33fb20acf363e469e8ed78c09a9098c", "type_name": "中出"},
    {"type_id": "a4814e695b2ecfc35571261b8ef61d22", "type_name": "内射"},
    {"type_id": "acb2fff953a2fc113feb9291acf42f1a", "type_name": "啪啪"},
    {"type_id": "978b25a74287b9460f6ada67a09bc88c", "type_name": "白虎"},
    {"type_id": "081dcb0707dbf724ff2288b8ff26d986", "type_name": "自拍"},
    {"type_id": "e33cc5c74cbaff91e5708e787baf7cb1", "type_name": "合集"},
    {"type_id": "c4427022dc5bdbe8503d905e7cc02eb3", "type_name": "福利"},
    {"type_id": "6507c6a0e88c6c7e5697954e5e298675", "type_name": "主播"},
    {"type_id": "449fb65a4e573a79f841806867176c48", "type_name": "女神"},
    {"type_id": "2f62dec4a397b6a623431560eb75f31c", "type_name": "母狗"},
    {"type_id": "ff0dab09a85e14aca3ae3d3add1f21a6", "type_name": "荡妇"},
    {"type_id": "76c630d4dbb32cf90cc1e8dd448fafac", "type_name": "奇闻趣事"},
    {"type_id": "e4e1d3efc7b6b8f6ab1710e7a507bcb5", "type_name": "大乳房"},
    {"type_id": "478ac59966b81472230b7a1ad0b62c62", "type_name": "美丽的胸部"},
    {"type_id": "ac966f94352daed5af9df932b9790dae", "type_name": "反差"},
    {"type_id": "ac99bd13252867b827d283fc86cb8faf", "type_name": "细长的"},
    {"type_id": "0053940855c6f53434b1e2ab3108ce4a", "type_name": "业余"},
    {"type_id": "dd8b8266543a2a94c2439da757ccbc6d", "type_name": "美丽的女孩"},
    {"type_id": "628f137420927a319756451b39f716f1", "type_name": "高视力"},
    {"type_id": "594df1249e1ffe309cc0f1757a2f0c53", "type_name": "独家的"},
    {"type_id": "571a16325e48458862fa3253cb2b9750", "type_name": "单一作品"},
    {"type_id": "6c3afde44e16da0e78ff332970933fee", "type_name": "仅限送货"},
    {"type_id": "4k", "type_name": "4K"},
    {"type_id": "3fb45bdb43ca4aee2690ebaeffb973bc", "type_name": "推特"},
    {"type_id": "onlyfans", "type_name": "OnlyFans"},
    {"type_id": "f6dd4a7cc63f05cf7bd3b52bd45073ec", "type_name": "最新"},
    {"type_id": "6b8a7db8f9f181757eb1f3bd1bbf4b80", "type_name": "淫妻"},
    {"type_id": "e1132ac433d65a9f6b73d5c2a7d71370", "type_name": "网红2"},
    {"type_id": "0773312bdeb075a53eefa401d99ec9cd", "type_name": "口交2"},
    {"type_id": "827a793aea37e65a5e4de82dac880eab", "type_name": "工具"},
    {"type_id": "ol7", "type_name": "哦"},
]

class Spider(Spider):
    def init(self, extend=None):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': UA})
        self.HOST = HOST
        for host in HOSTS:
            self.session.cookies.set('_safe', '1', domain=host.split('//')[1], path='/')
        for host in HOSTS:
            try:
                r = self.session.get(host + '/new/', timeout=8)
                if r.status_code == 200 and '/video/' in r.text:
                    self.HOST = host
                    break
            except Exception:
                continue

    def _pic(self, url):
        url = re.sub(r'https?://[^/]+/', 'https://bmc2.imgclh.com/', url)
        return 'https://wsrv.nl/?url=%s&output=jpeg' % quote(url, safe='')

    def _s(self, reset=False):
        if reset or not hasattr(self, 'session'):
            self.init()
        return self.session

    def _get(self, url, params=None, timeout=10):
        last = None
        for _ in range(3):
            try:
                r = self._s().get(url, params=params, timeout=timeout)
                if r.status_code == 200:
                    return r
                last = 'HTTP%d' % r.status_code
            except Exception as e:
                last = type(e).__name__
        return None

    def _items(self, t):
        rows = []
        for u, name, pic in re.findall(r'href="(https://[^/"]+/video/\d+/[^"]+)"[^>]*title="([^"]*)"[\s\S]*?data-original="([^"]+)"[\s\S]*?</a>', t):
            rows.append({'vod_id': u[len(self.HOST):], 'vod_name': name.strip(), 'vod_pic': self._pic(pic), 'vod_remarks': ''})
        return rows

    def _pagecount(self, t):
        ms = re.findall(r'from:(\d+)', t)
        if ms:
            return max(int(x) for x in ms) // 20 + 1
        m = re.search(r'最后\s*->\s*[^"]*?/(\d+)/', t)
        return int(m.group(1)) if m else 1

    def homeContent(self, filter=False):
        r = self._get(self.HOST + '/new/')
        return {'class': CATEGORIES, 'list': self._items(r.text) if r else []}

    def homeVideoContent(self):
        r = self._get(self.HOST + '/new/')
        return {'list': self._items(r.text) if r else []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        try:
            pg = int(pg or 1)
            if tid == 'new':
                url = self.HOST + '/new/' if pg == 1 else self.HOST + '/new/%d/' % pg
            else:
                url = self.HOST + '/tags/%s/' % tid if pg == 1 else self.HOST + '/tags/%s/%d/' % (tid, pg)
            r = self._get(url)
            if r is None:
                r = self._get(url.replace(self.HOST, next(h for h in HOSTS if h != self.HOST)))
                if r is None:
                    return {'list': [], 'page': pg, 'pagecount': pg}
                self.HOST = next(h for h in HOSTS if h != self.HOST)
            t = r.text
        except Exception:
            return {'list': [], 'page': pg, 'pagecount': 0}
        return {'list': self._items(t), 'page': pg, 'pagecount': self._pagecount(t)}

    def detailContent(self, ids):
        self._s()
        u = ids[0]
        if not u.startswith('http'):
            u = self.HOST + u
        r = self._get(u)
        if r is None:
            for h in HOSTS:
                if h == self.HOST:
                    continue
                r = self._get(u.replace(self.HOST, h))
                if r:
                    self.HOST = h
                    break
            if r is None:
                return {'list': []}
        t = r.text
        title = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', t)
        desc = re.search(r'id="description"[^>]*>([\s\S]*?)</', t)
        dur = re.search(r'video:duration"\s+content="(\d+)"', t)
        pj = re.search(r'Playerjs\s*\(\s*\{([\s\S]*?)\}\s*\)', t)
        file = None
        poster = None
        if pj:
            m = re.search(r'file\s*:\s*["\']([^"\']+)', pj.group(1))
            if m:
                file = m.group(1)
            m = re.search(r'poster\s*:\s*["\']([^"\']+)', pj.group(1))
            if m:
                poster = m.group(1)
        if not poster:
            m = re.search(r'property="og:image"[^>]*content="([^"]+)"', t)
            if m:
                poster = m.group(1)
        if not file:
            m = re.search(r'/video/(\d+)/', u)
            if m:
                vid = int(m.group(1))
                file = 'https://r22.jb-aiwei.cc/videos/%d/%d/%dvideo_limt.mp4' % (vid // 1000 * 1000, vid, vid)
        sf = None
        if pj:
            m = re.search(r'file\s*:\s*["\']([^"\']+)', pj.group(1))
            if m:
                sf = m.group(1)
        lines = [file]
        names = ['直链']
        if sf and sf != file:
            lines.append(sf)
            names.append('网页')
        remark = '试看'
        if dur:
            remark = 'HD · %d分钟 试看' % (int(dur.group(1)) // 60)
        vod = {
            'vod_id': u,
            'vod_name': title.group(1).strip() if title else '',
            'vod_pic': self._pic(poster) if poster else '',
            'vod_content': desc.group(1).strip() if desc else '',
            'vod_remarks': remark,
            'vod_play_from': '$$$'.join(names),
            'vod_play_url': '$$$'.join('播放$%s' % x for x in lines),
        }
        return {'list': [vod]}

    def searchContent(self, key, quick=False):
        r = self._get(self.HOST + '/search/', params={'q': key})
        return {'list': self._items(r.text) if r else []}

    def playerContent(self, flag, pid, vipFlags=None):
        return {'parse': 0, 'url': pid, 'header': {'User-Agent': UA, 'Referer': self.HOST + '/', 'Origin': self.HOST}}

    def localProxy(self, param):
        url = param.get('url') if isinstance(param, dict) else None
        if not url:
            return None
        r = self._s().get(url, headers={'Referer': self.HOST + '/'}, stream=True, timeout=15)
        for chunk in r.iter_content(65536):
            if chunk:
                yield chunk