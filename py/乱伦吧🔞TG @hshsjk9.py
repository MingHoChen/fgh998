# -*- coding: utf-8 -*-
"""乱Lun吧 www.raonro8.buzz/go - 四壳通用 Spider"""
import re, json, time
try:
    from urllib.parse import urljoin, urlparse, parse_qs
    from urllib.request import Request, urlopen
except Exception:
    from urlparse import urljoin, urlparse, parse_qs
    from urllib2 import Request, urlopen

try:
    import requests
except Exception:
    requests = None

BASE = "https://1d877b2g.chnudyharena.buzz"
UA = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"
CATS = {
    "61": "森林资源", "347": "乐播资源", "48": "桃花资源", "365": "番号资源",
    "132": "杏吧资源", "423": "麻豆资源", "18": "大地资源",
    "160": "成人动漫", "5": "热门事件", "6": "传媒自拍"
}

class _Http(object):
    def __init__(self):
        self.s = requests.Session() if requests else None
        if self.s:
            self.s.headers.update({"User-Agent": UA, "Referer": BASE + "/bar/"})
    def get(self, url, timeout=20):
        if self.s:
            r = self.s.get(url, timeout=timeout, allow_redirects=True)
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        req = Request(url, headers={"User-Agent": UA, "Referer": BASE + "/bar/"})
        return urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")
    def bytes(self, url, timeout=20):
        if self.s:
            return self.s.get(url, timeout=timeout).content
        req = Request(url, headers={"User-Agent": UA, "Referer": BASE + "/bar/"})
        return urlopen(req, timeout=timeout).read()

class Spider:
    _play_cache = {}
    def __init__(self):
        self.s = _Http()
        self.session = self.s
        self.sess = self.s
        self.home = BASE

    def getDependence(self):
        return []

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.home = extend.get("host") or extend.get("url") or BASE
        elif isinstance(extend, str) and extend.strip():
            self.home = extend.strip().rstrip("/")
        if not self.home.startswith("http"):
            self.home = BASE
        return None

    def _url(self, path):
        return urljoin(self.home + "/", path)

    def _clean(self, x):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x or "")).strip()

    def _cards(self, text):
        out, seen = [], set()
        pat = re.compile(r'<div[^>]+class=["\']vod["\'][^>]*>(.*?)(?=\n\s*<div[^>]+class=["\']vod["\']|\Z)', re.S|re.I)
        for block in pat.findall(text):
            m = re.search(r'href=["\']([^"\']*?/voddetail/[^"\']+)["\']', block, re.I)
            if not m:
                continue
            vid = urljoin(self.home, m.group(1))
            if vid in seen: continue
            im = re.search(r'(?:data-src|src)=["\']([^"\']+)', block, re.I)
            nm = re.search(r'<div[^>]+class=["\']vod-txt["\'][^>]*>.*?<a[^>]*>(.*?)</a>', block, re.S|re.I)
            name = self._clean(nm.group(1) if nm else "")
            if not name: continue
            pic = urljoin(self.home, im.group(1)) if im else ""
            out.append({"vod_id": vid, "vod_name": name, "vod_pic": pic, "vod_remarks": ""})
            seen.add(vid)
        return out

    def _pagecount(self, text):
        nums = []
        for x in re.findall(r'(?:vodtype/\d+-|vodtype/\d+/\?page=|page/)(\d+)', text, re.I):
            try: nums.append(int(x))
            except: pass
        return max(nums or [1])

    def homeContent(self, filter=None):
        text = self.s.get(self._url("/bar/"))
        vs = self._cards(text)
        return {"class": [{"type_id": k, "type_name": v} for k,v in CATS.items()], "filters": {}, "list": vs}

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        tid = str(tid); pg = int(pg or 1)
        path = "/vodtype/%s/" % tid if pg == 1 else "/vodtype/%s-%s/" % (tid, pg)
        text = self.s.get(self._url(path))
        return {"page": pg, "pagecount": self._pagecount(text), "limit": 48, "total": 0, "list": self._cards(text)}

    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)): ids = ids[0] if ids else ""
        text = self.s.get(urljoin(self.home + "/", str(ids)))
        title = ""
        for p in [r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', r'<title>(.*?)</title>']:
            m = re.search(p, text, re.S|re.I)
            if m:
                title = self._clean(m.group(1)); break
        if title.startswith('-') or '乱Lun吧' in title:
            title = ''
        if not title:
            m = re.search(r'<a[^>]+class=["\'][^"\']*play-btn[^"\']*["\'][^>]*>.*?</a>', text, re.S|re.I)
            title = self._clean(re.search(r'<title>(.*?)</title>', text, re.S|re.I).group(1)) if re.search(r'<title>(.*?)</title>', text, re.S|re.I) else '视频详情'
        pic = ""
        m = re.search(r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\']([^"\']+)', text, re.I)
        if m: pic = urljoin(self.home, m.group(1))
        if not pic:
            m = re.search(r'(?:data-src|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)', text, re.I)
            if m: pic = urljoin(self.home, m.group(1))
        desc = ""
        for p in [r'<div[^>]+class=["\'][^"\']*(?:vod-content|content|desc)[^"\']*["\'][^>]*>(.*?)</div>', r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)']:
            m = re.search(p, text, re.S|re.I)
            if m: desc = self._clean(m.group(1)); break
        links = []
        for m in re.finditer(r'href=["\']([^"\']*/vodplay/[^"\']+)["\'][^>]*[^>]*>(.*?)</a>', text, re.S|re.I):
            label = self._clean(m.group(2)) or "第1集"
            links.append(label + "$" + urljoin(self.home, m.group(1)))
        if not links:
            m = re.search(r'href=["\']([^"\']*/vodplay/[^"\']+)', text, re.I)
            if m: links = ["第1集$" + urljoin(self.home, m.group(1))]
        return {"list": [{"vod_id": str(ids), "vod_name": title, "vod_pic": pic, "vod_content": desc, "vod_play_from": "乱Lun吧", "vod_play_url": "#".join(links)}]}

    def searchContent(self, key, quick=False, pg="1"):
        pg = int(pg or 1)
        kw = str(key).strip()
        path = "/vodsearch/%s----------%s---/" % (kw, pg)
        text = self.s.get(self._url(path))
        return {"page": pg, "pagecount": self._pagecount(text), "limit": 48, "total": 0, "list": self._cards(text)}

    def playerContent(self, flag, ids, vipFlags=None):
        url = str(ids)
        now = time.time()
        hit = self._play_cache.get(url)
        if hit and hit[1] > now: stream = hit[0]
        else:
            text = self.s.get(urljoin(self.home + "/", url))
            m = re.search(r'var\s+player_data\s*=\s*(\{.*?\})\s*</script>', text, re.S|re.I)
            if not m: m = re.search(r'var\s+player_data\s*=\s*(\{.*?\})', text, re.S|re.I)
            if not m: return {"parse": 0, "url": "", "header": {"User-Agent": UA}}
            try:
                d = json.loads(m.group(1).replace('\\/', '/'))
                stream = d.get("url", "")
                if int(d.get("encrypt", 0) or 0) == 1:
                    from urllib.parse import unquote
                    stream = unquote(stream)
            except Exception:
                stream = ""
            self._play_cache[url] = (stream, now + 900)
        return {"parse": 0, "url": stream, "header": {"User-Agent": UA, "Referer": urljoin(self.home, "/")}, "format": "application/x-mpegURL"}

    def localProxy(self, param):
        if isinstance(param, dict): q = param
        else:
            try: q = json.loads(param)
            except Exception: q = {k: v[0] for k,v in parse_qs(str(param)).items()}
        u = q.get("url", "") or q.get("uri", "")
        if not u: return [404, "text/plain", b"", {}]
        data = self.s.bytes(u)
        if b"#EXTM3U" in data[:1000]:
            base = u.rsplit("/", 1)[0] + "/"
            lines = data.decode("utf-8", "ignore").splitlines()
            data = ("\n".join(urljoin(base, x) if x and not x.startswith("#") else x for x in lines)).encode()
            return [200, "application/vnd.apple.mpegurl", data, {"Cache-Control": "no-cache"}]
        return [200, "video/mp2t", data, {"Cache-Control": "no-cache"}]

    def action(self, action): return {}
    def destroy(self): return None
    def manualVideoCheck(self): return False
    def isVideoFormat(self, url): return ".m3u8" in str(url).lower() or ".mp4" in str(url).lower()
    def getName(self): return "乱Lun吧"
