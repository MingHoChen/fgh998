# -*- coding: utf-8 -*-
"""
91Hub Spider - 修复版
修复：1）域名后缀从发布站动态提取 2）parse_videos正则兼容data属性
"""
import sys
import json
import re
import base64
import random
import string
import time
import requests
from Crypto.Cipher import AES
from urllib.parse import unquote

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def getName(self):
        return "91Hub视频"

    def init(self, extend=""):
        self.xurl = self.get_domain().rstrip('/')
        self.session = requests.Session()
        self.headerx = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 16; 2407FRK8EC Build/BP2A.250605.031.A3) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/137.0.7151.115 Mobile Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.header = {'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36'}

    # ========== 1. 域名自动获取（从发布站动态提取后缀） ==========
    def get_domain(self):
        # 从发布站提取动态后缀
        suffixes = self._fetch_suffixes()
        if not suffixes:
            suffixes = ['.9jht6.cc', '.ogmqj.cc']
        chars = string.ascii_lowercase + string.digits
        for _ in range(6):
            prefix = ''.join(random.choices(chars, k=5))
            suffix = random.choice(suffixes)
            domain = f"https://{prefix}{suffix}"
            try:
                resp = requests.get(domain, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                if resp.status_code == 200:
                    return domain
            except Exception:
                pass
        for fallback in ["https://91hubw.com", "https://91hubs.com"]:
            try:
                resp = requests.get(fallback, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                if resp.status_code == 200:
                    return fallback
            except Exception:
                pass
        return "https://91hubw.com"

    def _fetch_suffixes(self):
        """从发布站 https://91hubx.com/ 提取动态域名后缀"""
        try:
            r = requests.get("https://91hubx.com/", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            if r.status_code != 200:
                return []
            html = r.text
            # 提取 words.random() + '.xxx.xxx' 格式的后缀
            suffixes = re.findall(r"words\.random\(\)\s*\+\s*['\"](\.[a-z0-9]+\.[a-z]{2,6})['\"]", html)
            # 去重并保持顺序
            seen = set()
            result = []
            for s in suffixes:
                if s not in seen:
                    seen.add(s)
                    result.append(s)
            return result
        except Exception:
            return []

    # ========== 2. 基础请求与工具 ==========
    def fetch(self, url):
        try:
            h = dict(self.headerx)
            h["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            h["Referer"] = self.xurl + "/"
            r = self.session.get(url=url, headers=h, timeout=15)
            return r.text if r.status_code == 200 else ""
        except Exception:
            return ""

    def _href(self, href):
        if not href:
            return ""
        return self.xurl + href if href.startswith('/') else href

    def _img(self, src):
        if not src or not src.startswith('http') or src.startswith('data:'):
            return ''
        b = base64.b64encode(src.encode('utf-8')).decode('ascii')
        return f"{self.getProxyUrl()}&type=pic&url={b}"

    def _build(self, vid, name, pic='', remark='', desc=''):
        return {"vod_id": vid, "vod_name": name, "vod_pic": pic, "vod_remarks": remark, "vod_content": desc}

    def _result(self, videos, pg, pagecount=9999):
        return {"list": videos, "page": pg, "pagecount": pagecount, "limit": 24, "total": 999999 if pagecount > 1 else len(videos)}

    def _parse_ext(self, ext):
        if not ext:
            return {}
        if isinstance(ext, dict):
            return ext
        if isinstance(ext, str):
            ext = ext.strip()
            if not ext or ext in ("{}", "null", "undefined"):
                return {}
            try:
                return json.loads(ext)
            except Exception:
                result = {}
                for part in ext.split("&"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        result[k] = v
                return result
        return {}

    # ========== 3. 页面解析（修复：video-item 兼容 data 属性） ==========
    def parse_videos(self, html):
        videos = []
        if not html:
            return videos
        seen = set()
        # 修复：用 [^>]* 兼容 <div class="video-item" data-xxx="..."> 格式
        blocks = re.findall(
            r'<div class="video-item"[^>]*>(.*?)<div class="video-preview w-full h-full left-0 top-0">',
            html, re.S
        )
        for block in blocks:
            href = re.search(r'href="([^"]+)"', block)
            if not href:
                continue
            link = href.group(1)
            m = re.search(r'/(?:video|av)/(\d+)/', link)
            vid = m.group(1) if m else link
            if vid in seen:
                continue
            seen.add(vid)
            alt = re.search(r'alt="([^"]*)"', block)
            title = alt.group(1).strip() if alt else vid
            ds = re.search(r'data-src="([^"]+)"', block)
            pic = self._img(ds.group(1)) if ds else ''
            remark = ''
            rm = re.search(
                r'<div class="text-sm opacity-50 py-0\.5 px-1\.5 bg-black rounded-large text-white">\s*([^<]+)\s*</div>',
                block
            )
            if rm:
                remark = rm.group(1).strip()
            skip_words = ['棋牌', '约炮', '春药', 'PG', '注册', '下载', '澳门', '金沙',
                          '威尼斯', '彩票', '博彩', '捕鱼', '开元', '葡京', '同城', '裸聊', '直播']
            if any(kw in title for kw in skip_words):
                continue
            videos.append(self._build(vid, title, pic, remark))
        return videos

    def parse_movie_themes(self, html):
        videos = []
        blocks = re.findall(r'<li[^>]*class="[^"]*theme-item[^"]*"[^>]*>(.*?)</li>', html, re.S)
        for block in blocks:
            href = re.search(r'href="([^"]+)"', block)
            if not href:
                continue
            url = href.group(1)
            m = re.search(r'/movie/([^/]+)/', url)
            slug = m.group(1) if m else ''
            if not slug:
                continue
            alt = re.search(r'alt="([^"]*)"', block)
            title = alt.group(1).strip() if alt else slug
            ds = re.search(r'data-src="([^"]+)"', block)
            pic = self._img(ds.group(1)) if ds else ''
            remark = ''
            rm = re.search(r'text-white[^>]*group-hover:text-primary">\s*([^<]+)\s*</div>', block)
            if rm:
                remark = rm.group(1).strip()
            videos.append(self._build(f"movie/{slug}", title, pic, remark, desc=title))
            videos[-1]["vod_tag"] = "folder"
        return videos

    def parse_av_themes(self, html):
        videos = []
        blocks = re.findall(r'<li[^>]*class="[^"]*theme-item[^"]*"[^>]*>(.*?)</li>', html, re.S)
        for block in blocks:
            href = re.search(r'href="([^"]+)"', block)
            if not href:
                continue
            url = href.group(1)
            m = re.search(r'/av/theme/([^/]+)/', url)
            slug = m.group(1) if m else ''
            if not slug:
                continue
            alt = re.search(r'alt="([^"]*)"', block)
            title = alt.group(1).strip() if alt else slug
            ds = re.search(r'data-src="([^"]+)"', block)
            pic = self._img(ds.group(1)) if ds else ''
            remark = ''
            rm = re.search(r'text-white[^>]*group-hover:text-primary">\s*([^<]+)\s*</div>', block)
            if rm:
                remark = rm.group(1).strip()
            videos.append(self._build(f"av/theme/{slug}", title, pic, remark, desc=title))
            videos[-1]["vod_tag"] = "folder"
        return videos

    def parse_actors(self, html):
        videos = []
        blocks = re.findall(r'<li[^>]*class="[^"]*group[^"]*"[^>]*>(.*?)</li>', html, re.S)
        for block in blocks:
            href = re.search(r'href="([^"]+)"', block)
            if not href:
                continue
            url = href.group(1)
            if '/actresses/' not in url:
                continue
            m = re.search(r'/actresses/([^/]+)/', url)
            name = m.group(1) if m else ''
            name = unquote(name)
            if not name:
                continue
            alt = re.search(r'alt="([^"]*)"', block)
            title = alt.group(1).strip() if alt else name
            ds = re.search(r'data-src="([^"]+)"', block)
            pic = self._img(ds.group(1)) if ds else ''
            remark = ''
            rm = re.search(r'<span class="text-sm">\s*([^<]+)\s*</span>', block)
            if rm:
                remark = rm.group(1).strip()
            videos.append(self._build(f"actresses/{name}", title, pic, remark, desc=title))
            videos[-1]["vod_tag"] = "folder"
        return videos

    # ========== 4. TVBox标准接口 ==========
    def homeContent(self, filter):
        classes = [
            {"type_id": "latest", "type_name": "最近更新"},
            {"type_id": "movie", "type_name": "分类合集"},
            {"type_id": "av", "type_name": "岛国AV"},
            {"type_id": "av_theme", "type_name": "AV主题"},
            {"type_id": "actors", "type_name": "AV女优"},
                    ]
        filters = {
            "latest": [
                {"key": "by", "name": "排序", "value": [
                    {"n": "近期最佳", "v": "hot"},
                    {"n": "最近更新", "v": "latest"},
                    {"n": "最多观看", "v": "popular"},
                    {"n": "最多收藏", "v": "favorites"}
                ]}
            ],
            "movie": [
                {"key": "by", "name": "影片排序", "value": [
                    {"n": "近期最佳", "v": "hot"},
                    {"n": "最近更新", "v": "latest"},
                    {"n": "最多观看", "v": "popular"},
                    {"n": "最多收藏", "v": "favorites"}
                ]}
            ],
            "av": [
                {"key": "cateId", "name": "类型", "value": [
                    {"n": "近期更新", "v": "update"},
                    {"n": "最新上市", "v": "new"},
                    {"n": "热门影片", "v": "hotmovie"}
                ]}
            ],
            "av_theme": [
                {"key": "by", "name": "影片排序", "value": [
                    {"n": "最佳", "v": "week"},
                    {"n": "更新", "v": "update"},
                    {"n": "观看", "v": "hot"},
                    {"n": "收藏", "v": "collect"}
                ]}
            ],
            "actors": [
                {"key": "by", "name": "女优排序", "value": [
                    {"n": "热度优先", "v": "hot"},
                    {"n": "最近更新", "v": "update"},
                    {"n": "最多影片", "v": "video"},
                    {"n": "名称排序", "v": "name"}
                ]},
                {"key": "by2", "name": "影片排序", "value": [
                    {"n": "最佳", "v": "week"},
                    {"n": "更新", "v": "update"},
                    {"n": "观看", "v": "hot"},
                    {"n": "收藏", "v": "collect"}
                ]}
            ],
        }
        return {"class": classes, "list": [], "filters": filters}

    def homeVideoContent(self):
        html = self.fetch(f"{self.xurl}/")
        videos = self.parse_videos(html)
        return {"list": videos[:12]}

    def categoryContent(self, cid, pg, filter, ext):
        page = int(pg) if pg else 1
        ext = self._parse_ext(ext)

        if cid == "latest":
            by = ext.get('by', 'latest')
            url = f"{self.xurl}/movie/tjgn/{by}/page/{page}/"
            return self._result(self.parse_videos(self.fetch(url)), page, 9999)

        if cid == "av":
            cateId = ext.get('cateId', 'update')
            url = f"{self.xurl}/av/{cateId}/page/{page}/"
            return self._result(self.parse_videos(self.fetch(url)), page, 9999)

        if cid == "movie":
            url = f"{self.xurl}/movie/"
            if page > 1:
                url = f"{self.xurl}/movie/page/{page}/"
            return self._result(self.parse_movie_themes(self.fetch(url)), page, 1)

        if cid.startswith("movie/"):
            slug = cid[6:]
            by = ext.get('by', 'latest')
            url = f"{self.xurl}/movie/{slug}/{by}/page/{page}/"
            return self._result(self.parse_videos(self.fetch(url)), page, 9999)

        if cid == "av_theme":
            url = f"{self.xurl}/av/theme/"
            if page > 1:
                url = f"{self.xurl}/av/theme/page/{page}/"
            return self._result(self.parse_av_themes(self.fetch(url)), page, 1)

        if cid.startswith("av/theme/"):
            slug = cid[9:]
            by = ext.get('by', 'week')
            url = f"{self.xurl}/av/theme/{slug}/{by}/page/{page}/"
            return self._result(self.parse_videos(self.fetch(url)), page, 9999)

        if cid == "actors":
            by = ext.get('by', 'hot')
            url = f"{self.xurl}/actors/{by}/page/{page}/"
            return self._result(self.parse_actors(self.fetch(url)), page, 9999)

        if cid.startswith("actresses/"):
            name = cid[10:]
            by = ext.get('by2', 'week')
            url = f"{self.xurl}/actresses/{name}/{by}/page/{page}/"
            return self._result(self.parse_videos(self.fetch(url)), page, 9999)

        return self._result([], page, 1)

    # ========== 5. 详情与播放 ==========
    def detailContent(self, ids):
        did = ids[0]
        vod_id = did
        url = f"{self.xurl}/video/{vod_id}/"
        html = self.fetch(url)
        if not html:
            url2 = f"{self.xurl}/av/{vod_id}/"
            html = self.fetch(url2)
            if not html:
                return {"list": []}

        vod_name = vod_id
        poster = ""
        vod_remarks = ""
        vod_content = ""

        tm = re.search(r'<h1[^>]*class="[^"]*dx-title[^"]*"[^>]*>(.*?)</h1>', html, re.S)
        if tm:
            vod_name = re.sub(r'<[^>]+>', '', tm.group(1)).strip()

        m = re.search(r'const\s+_detail_\s*=\s*(\{[^}]+\})', html)
        if m:
            try:
                detail = json.loads(m.group(1))
                if not vod_name or vod_name == vod_id:
                    vod_name = detail.get("title", vod_id)
                poster = detail.get("poster", "")
            except Exception:
                pass

        um = re.search(r'icons\.svg#time"[^>]*>\s*</use>\s*</svg>\s*([^<]+)', html)
        if um:
            update_time = um.group(1).strip()
            if update_time:
                vod_remarks = update_time

        hm = re.search(r'class="[^"]*hot-div[^"]*"[^>]*>.*?([0-9]+)\s*</div>', html, re.S)
        if hm:
            hot_num = hm.group(1).strip()
            if hot_num:
                vod_remarks = f"🔥{hot_num}" + (f" | {vod_remarks}" if vod_remarks else "")

        dm = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
        if dm:
            vod_content = dm.group(1).strip()

        poster = self._img(poster) if poster else ""
        play_url = self._get_real_play_url(html)

        vod = {
            "vod_id": str(vod_id),
            "vod_name": vod_name,
            "vod_pic": poster,
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": vod_remarks,
            "vod_actor": "",
            "vod_director": "",
            "vod_content": vod_content,
            "vod_play_from": "默认线路",
            "vod_play_url": f"播放${play_url}" if play_url else "",
        }
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        url = id if str(id).startswith("http") else self._href(id)
        return {"parse": 0, "playUrl": "", "url": url, "header": self.header}

    # ========== 6. 搜索 ==========
    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, page):
        pg = int(page) if page else 1
        url = f"{self.xurl}/search/{key}/"
        if pg > 1:
            url = f"{self.xurl}/search/{key}/page/{pg}/"
        html = self.fetch(url)
        videos = self.parse_videos(html)
        return {"page": pg, "pagecount": pg + 1 if len(videos) >= 20 else pg, "limit": 20, "total": 0, "list": videos}

    # ========== 7. 图片代理与解密 ==========
    def localProxy(self, params):
        if params.get('type') == "pic":
            return self.proxyPic(params)
        return None

    def proxyPic(self, params):
        url = base64.b64decode(params['url']).decode('utf-8')
        data = self.decrypt_image(requests.get(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': self.xurl + '/'}).content)
        ext = self.detect_extension(data)
        mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}
        return [200, mime.get(ext, 'application/octet-stream'), data]

    def decrypt_image(self, encrypted_data):
        dec = AES.new(b'f5d965df75336270', AES.MODE_CBC, b'97b60394abc2fbe1').decrypt(encrypted_data)
        pad = dec[-1]
        if 1 <= pad <= 16 and dec[-pad:] == bytes([pad]) * pad:
            dec = dec[:-pad]
        else:
            dec = dec.rstrip(b'\x00')
        return dec

    def detect_extension(self, data):
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return 'png'
        if data[:3] == b'\xff\xd8\xff':
            return 'jpg'
        if data[:6] in (b'GIF87a', b'GIF89a'):
            return 'gif'
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return 'webp'
        return 'bin'

    # ========== 8. 播放解密 ==========
    def _get_real_play_url(self, html):
        try:
            config = self._parse_config(html)
            if not config or not config.get("api") or not config.get("key"):
                return ""
            api_url = self.xurl + config["api"]
            r = self.session.get(api_url, headers={
                "User-Agent": self.header["User-Agent"],
                "Referer": self.xurl + "/",
            }, verify=False, timeout=15)
            result = r.json()
            if result.get("code") != 200 or not result.get("data"):
                return ""
            raw = base64.b64decode(result["data"])
            key = config["key"].encode()
            iv = config["iv"].encode() if config.get("iv") else key
            cipher = AES.new(key, AES.MODE_CBC, iv)
            dec = cipher.decrypt(raw)
            pad = dec[-1]
            if 1 <= pad <= 16:
                dec = dec[:-pad]
            play_url = dec.decode('utf-8', errors='replace')
            if play_url.startswith("http"):
                return play_url
            return ""
        except Exception:
            return ""

    def _parse_config(self, html):
        try:
            idx = html.find('eval(function(p,a,c,k,e,d)')
            if idx < 0:
                return None
            end = html.find('</script>', idx)
            code = html[idx:end]
            m = re.search(r"',(\d+),(\d+),'", code)
            if not m:
                return None
            p_end = m.start()
            p_str = code[code.find("}('")+3:p_end]
            a_val = int(m.group(1))
            c_val = int(m.group(2))
            k_start = m.end()
            split_pos = code.find(".split", k_start)
            if split_pos < 0:
                return None
            k_str = code[k_start:split_pos].strip("'")
            k_list = k_str.split('|')
            chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
            def b62(cc):
                res = ''
                while cc >= a_val:
                    res = chars[cc % a_val] + res
                    cc = cc // a_val
                return chars[cc] + res
            decoded = p_str
            for i in range(c_val-1, -1, -1):
                if i < len(k_list) and k_list[i]:
                    token = b62(i)
                    decoded = re.sub(r'\b'+re.escape(token)+r'\b', k_list[i], decoded)
            decoded = decoded.replace("\\'", "'").replace('\\"', '"')
            config = {}
            for key_name in ['api', 'key', 'iv', 'h264_api']:
                m2 = re.search(rf"['\"]{key_name}['\"]\s*:\s*\"([^\"]+)\"", decoded)
                if m2:
                    config[key_name] = m2.group(1).replace('\\/', '/')
            return config
        except Exception:
            return None

    def destroy(self):
        pass

    def close(self):
        self.destroy()
