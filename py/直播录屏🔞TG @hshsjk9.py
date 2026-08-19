# coding=utf-8
# ============================
# 直播录屏 - TVBox/HKL/CatVod 兼容源
# CMS: 苹果CMS v10 (maccms) + ecms337模板 + DPlayer
# 生成器: 遮天·极道帝兵·万法归一 v4.0
# 站点: https://www.zhiboluping.com/ (发布页: https://page2.kanluping.com/)
# ============================
import sys
import json
import re
import urllib.parse
from lxml import etree

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    BaseSpider = object


class Spider(BaseSpider if BaseSpider is not object else object):
    def __init__(self):
        self.siteUrl = "https://www.zhiboluping.com"
        self.pubPage = "https://page2.kanluping.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://www.zhiboluping.com/",
        }
        self.cookies = {"age_verify": "1"}
        self.cateMap = {
            "01": {"name": "抖音快手", "path": "type01"},
            "free": {"name": "免费视频", "path": "free"},
            "27": {"name": "会议私播", "path": "type27"},
            "28": {"name": "偷拍系列", "path": "toupai/type28"},
            "03": {"name": "站长说", "path": "type03"},
        }
        self.timeout = 10

    # ------------------- HKL/CatVod 兼容 -------------------
    def getName(self):
        return "直播录屏"

    def init(self, extend=""):
        try:
            ext = json.loads(extend) if extend else {}
            if isinstance(ext, dict):
                if ext.get("host"):
                    self.siteUrl = ext["host"].rstrip("/")
                if ext.get("cookie"):
                    self.cookies.update(ext["cookie"])
                if ext.get("header") and isinstance(ext["header"], dict):
                    self.headers.update(ext["header"])
        except Exception:
            pass
        return

    def setExtendInfo(self, info):
        try:
            if isinstance(info, dict):
                if info.get("host"):
                    self.siteUrl = info["host"].rstrip("/")
                if info.get("cookie"):
                    self.cookies.update(info["cookie"])
                if info.get("header") and isinstance(info["header"], dict):
                    self.headers.update(info["header"])
        except Exception:
            pass
        return

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|flv|avi|mkv|rm|rmvb|wmv|mpg|mpeg|ts|webm)", url, re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def getDependence(self):
        return []

    def homeLayout(self):
        return True

    # ------------------- 网络请求封装 -------------------
    def _req(self, url, method="GET", data=None, headers=None, cookies=None):
        import requests
        import urllib3
        urllib3.disable_warnings()
        h = dict(self.headers)
        if headers:
            h.update(headers)
        c = dict(self.cookies)
        if cookies:
            c.update(cookies)
        try:
            if method.upper() == "POST":
                r = requests.post(url, data=data, headers=h, cookies=c, timeout=self.timeout, verify=False)
            else:
                r = requests.get(url, headers=h, cookies=c, timeout=self.timeout, verify=False)
            r.encoding = "utf-8"
            return r
        except Exception as e:
            print(f"[遮天] 请求异常: {url} -> {e}")
            return None

    def _fetchHtml(self, url):
        r = self._req(url)
        if r is None:
            return ""
        if "未满十八岁禁止观看" in r.text and "我知道了" in r.text:
            r = self._req(url, headers={"Referer": self.siteUrl + "/"})
            if r:
                r.encoding = "utf-8"
                return r.text
        return r.text

    # ------------------- 首页 -------------------
    def homeContent(self, filter):
        classes = []
        for tid, info in self.cateMap.items():
            classes.append({"type_id": tid, "type_name": info["name"]})
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        html = self._fetchHtml(self.siteUrl + "/")
        return self._parseListHtml(html)

    # ------------------- 分类 -------------------
    def categoryContent(self, tid, pg, filter, extend):
        info = self.cateMap.get(tid, {"path": tid})
        path = info["path"]
        if int(pg) <= 1:
            url = f"{self.siteUrl}/{path}/"
        else:
            url = f"{self.siteUrl}/{path}/index_{pg}.html"
        html = self._fetchHtml(url)
        result = self._parseListHtml(html)
        result["page"] = int(pg)
        result["pagecount"] = 9999
        result["limit"] = 24
        result["total"] = 99999
        return result

    # ------------------- 详情 -------------------
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        if vid.startswith("http"):
            url = vid
        else:
            url = f"{self.siteUrl}/{vid}.html" if not vid.endswith(".html") else f"{self.siteUrl}/{vid}"
        html = self._fetchHtml(url)
        tree = etree.HTML(html)

        # 标题
        title = ""
        for xp in ['//h1[@class="vodlist__title"]/text()', '//h1//text()', '//h2[@class="title"]/text()',
                   '//div[contains(@class,"vodinfo")]//h3/text()', '//div[contains(@class,"detail")]//h1/text()',
                   '//div[contains(@class,"detail-title")]//text()', '//div[contains(@class,"name")]//text()']:
            t = tree.xpath(xp)
            if t:
                title = str(t[0]).strip()
                break
        if not title:
            m = re.search(r'<title>(.*?)</title>', html)
            if m:
                title = m.group(1).split("-")[0].split("_")[0].strip()

        # 图片
        pic = ""
        for xp in ['//div[contains(@class,"detail-pic")]//img/@src', '//div[contains(@class,"vodlist__thumb")]//img/@data-original',
                   '//div[contains(@class,"pic")]//img/@src', '//div[contains(@class,"thumb")]//img/@src',
                   '//img[contains(@class,"lazy")]/@data-original', '//div[contains(@class,"detail")]//img/@src']:
            p = tree.xpath(xp)
            if p:
                pic = self._absUrl(str(p[0]).strip())
                break

        # 简介
        desc = ""
        for xp in ['//div[contains(@class,"content__detail")]//p/text()', '//div[contains(@class,"desc")]//text()',
                   '//div[contains(@class,"vodlist__desc")]//text()', '//div[contains(@class,"intro")]//p/text[contains(@class,"intro")]//p/text()',
                   '//div[contains(@class,"detail-info")]//p/text()', '//div[contains(@class,"info")]//p/text()']:
            d = tree.xpath(xp)
            if d:
                desc = "".join(d).strip()
                break

        # 从 maccms 变量提取 cid 和 aid，构造播放页 URL
        # 播放页: /e/DownSys/play/?classid={cid}&id={aid}
        playFrom = []
        playUrl = []
        maccms_match = re.search(r'var\s+maccms\s*=\s*({.+?});', html)
        if maccms_match:
            try:
                maccms = json.loads(maccms_match.group(1))
                cid = maccms.get("cid", "")
                aid = maccms.get("aid", "")
                if cid and aid:
                    play_page = f"{self.siteUrl}/e/DownSys/play/?classid={cid}&id={aid}"
                    playFrom.append("默认线路")
                    playUrl.append(f"播放${play_page}")
            except Exception:
                pass

        # 兜底：若未提取到 maccms，尝试从页面找任何播放链接
        if not playFrom:
            items = tree.xpath('//a[contains(@href,"/play/") or contains(@href,"/vodplay/") or contains(@href,"/e/DownSys/play/")]')
            if items:
                playFrom.append("默认线路")
                urls = []
                for a in items:
                    href = a.get('href', '')
                    text = "".join(a.xpath('.//text()')).strip() or "播放"
                    if href:
                        urls.append(f"{text}${self._absUrl(href)}")
                playUrl.append("#".join(urls))

        # 再兜底：iframe 直接嵌入
        if not playFrom:
            iframe_src = tree.xpath('//iframe[@src]/@src')
            if iframe_src:
                playFrom.append("默认线路")
                playUrl.append(f"播放${self._absUrl(str(iframe_src[0]))}")

        vod = {
            "vod_id": vid,
            "vod_name": title or "未知标题",
            "vod_pic": pic,
            "vod_content": desc,
            "vod_play_from": "$$$".join(playFrom) if playFrom else "默认线路",
            "vod_play_url": "$$$".join(playUrl) if playUrl else "",
        }
        return {"list": [vod]}

    # ------------------- 播放 -------------------
    def playerContent(self, flag, id, vipFlags):
        # id 是播放页完整 URL，如 https://www.zhiboluping.com/e/DownSys/play/?classid=26&id=15675
        url = id if id.startswith("http") else self._absUrl(id)
        html = self._fetchHtml(url)
        playUrl = ""

        # 检测是否需要登录
        if "您还没登录" in html or "login" in html.lower():
            # 需要登录，返回原始URL让TVBox尝试，或提示
            return {
                "parse": 1,
                "playUrl": "",
                "url": url,
                "header": json.dumps({
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.siteUrl + "/",
                    "Cookie": "age_verify=1"
                })
            }

        # DPlayer 配置提取: url: 'https://.../index.m3u8'
        m = re.search(r'url\s*:\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', html)
        if m:
            playUrl = m.group(1)
        # video: { url: '...' }
        if not playUrl:
            m = re.search(r'video\s*:\s*{\s*url\s*:\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', html, re.S)
            if m:
                playUrl = m.group(1)
        # MacPlayer 兼容
        if not playUrl:
            m = re.search(r'MacPlayer\.PlayUrl\s*=\s*["\'](.+?)["\']', html)
            if m:
                playUrl = m.group(1)
        # player_data JSON
        if not playUrl:
            m = re.search(r'player_data\s*=\s*({.+?})', html, re.S)
            if m:
                try:
                    pd = json.loads(m.group(1))
                    playUrl = pd.get("url", "")
                except Exception:
                    pass
        # var url = "..."
        if not playUrl:
            m = re.search(r'var\s+url\s*=\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', html)
            if m:
                playUrl = m.group(1)
        # 绝对路径 m3u8/mp4
        if not playUrl:
            m = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html)
            if m:
                playUrl = m.group(1)
        if not playUrl:
            m = re.search(r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']', html)
            if m:
                playUrl = m.group(1)
        # 相对路径 m3u8
        if not playUrl:
            m = re.search(r'["\'](/[^"\']+\.m3u8[^"\']*)["\']', html)
            if m:
                playUrl = self.siteUrl + m.group(1)

        # 相对路径转绝对路径
        if playUrl and playUrl.startswith("/"):
            playUrl = self.siteUrl + playUrl

        result = {
            "parse": 0 if playUrl else 1,
            "playUrl": "",
            "url": playUrl or url,
            "header": json.dumps({
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.siteUrl + "/",
                "Cookie": "age_verify=1"
            })
        }
        return result

    # ------------------- 搜索 -------------------
    def searchContent(self, key, quick):
        kw = urllib.parse.quote(key)
        urls = [
            f"{self.siteUrl}/vod/search.html?wd={kw}",
            f"{self.siteUrl}/?wd={kw}",
            f"{self.siteUrl}/search.html?wd={kw}",
        ]
        for url in urls:
            html = self._fetchHtml(url)
            if html and ("搜索结果" in html or "暂无数据" not in html or len(html) > 8000):
                result = self._parseListHtml(html)
                if result.get("list"):
                    return result
        return {"list": []}

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick)

    # ------------------- 通用列表解析 -------------------
    def _parseListHtml(self, html):
        tree = etree.HTML(html)
        videos = []

        all_li = tree.xpath('//li[contains(@class,"mb15")]')
        for li in all_li:
            a_tag = li.xpath('.//a[@href]')
            if not a_tag:
                continue
            href = a_tag[0].get('href', '')
            m = re.search(r'^/(?:free|type\d+|toupai/type\d+)(?:/[^/]+)*/(\d+)\.html$', href)
            if not m:
                continue
            vid_path = href[1:-5]

            title = ""
            if a_tag[0].get('title'):
                title = a_tag[0].get('title').strip()
            if not title:
                h2_a = li.xpath('.//h2//a/text()')
                if h2_a:
                    title = str(h2_a[0]).strip()
            if not title:
                alt = li.xpath('.//img/@alt')
                if alt:
                    title = str(alt[0]).strip()

            pic = ""
            for px in ['.//img/@src', './/img/@data-original', './/img/@data-src']:
                p = li.xpath(px)
                if p:
                    v = str(p[0]).strip()
                    if v and not v.startswith("data:"):
                        pic = self._absUrl(v)
                        break

            remark = ""
            for rx in ['.//span[contains(@class,"ico-left")]/text()', './/span[contains(@class,"ico-right")]/text()',
                       './/span[contains(@class,"remark")]/text()', './/span[contains(@class,"update")]/text()']:
                r = li.xpath(rx)
                if r:
                    remark = str(r[0]).strip()
                    break

            if title and vid_path:
                videos.append({
                    "vod_id": vid_path,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remark,
                })

        if not videos:
            a_tags = tree.xpath('//a[.//img[@src]]')
            for a in a_tags:
                href = a.get('href', '')
                m = re.search(r'^/(?:free|type\d+|toupai/type\d+)(?:/[^/]+)*/(\d+)\.html$', href)
                if not m:
                    continue
                vid_path = href[1:-5]
                title = a.get('title', '').strip()
                if not title:
                    alt = a.xpath('.//img/@alt')
                    if alt:
                        title = str(alt[0]).strip()
                pic = ""
                src = a.xpath('.//img/@src')
                if src:
                    pic = self._absUrl(str(src[0]).strip())
                remark = ""
                ico = a.xpath('.//span[contains(@class,"ico-left")]/text()')
                if ico:
                    remark = str(ico[0]).strip()
                if title and vid_path:
                    videos.append({
                        "vod_id": vid_path,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": remark,
                    })

        return {"list": videos}

    def _absUrl(self, url):
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        return self.siteUrl + ("" if url.startswith("/") else "/") + url

    def localProxy(self, param):
        return [200, "video/MP2T", "", ""]


def getSpider():
    return Spider()


if __name__ == "__main__":
    sp = Spider()
    print(json.dumps(sp.homeContent(None), ensure_ascii=False))
