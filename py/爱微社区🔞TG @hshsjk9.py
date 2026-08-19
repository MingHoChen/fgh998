# -*- coding: utf-8 -*-
#!/usr/bin/env python3

import re
import json
import time
import urllib.parse as urlparse

try:
    import requests as _requests
    _HAS_REQ = True
except ImportError:
    _HAS_REQ = False
    import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
SITE = "https://bav53.cc"
SITE_NAME = "爱微社区"


class Spider:
    name = SITE_NAME
    version = "1.1.0"

    def __init__(self):
        self.s = None
        self.session = None
        self.sess = None
        self.extend = ""
        self._safe = ""          # challenge cookie：_safe=<safeid>
        self._http_init()

    def _http_init(self):
        if _HAS_REQ:
            self.s = _requests.Session()
            self.s.verify = False
            self.s.headers.update({"User-Agent": UA, "Referer": SITE + "/"})
        self.session = self.s
        self.sess = self.s

    # ─────────── 基础请求（challenge 自动绕过）───────────
    def _fetch(self, url, referer=None, timeout=20):
        """GET url，自动处理 18+ JS 挑战：提取 safeid -> 带 _safe cookie 重请求。返回 bytes。"""
        hdrs = {"User-Agent": UA, "Accept": "*/*"}
        if referer:
            hdrs["Referer"] = referer
        for _attempt in range(4):
            if _HAS_REQ:
                if self._safe:
                    hdrs["Cookie"] = "_safe=" + self._safe
                try:
                    resp = self.s.get(url, headers=hdrs, timeout=timeout)
                    body = resp.content
                except Exception:
                    body = b""
            else:
                try:
                    req = urllib.request.Request(url, headers=hdrs)
                    with urllib.request.urlopen(req, timeout=timeout) as r:
                        body = r.read()
                except Exception:
                    body = b""
            text = body.decode("utf-8", "ignore")
            m = re.search(r"var\s+safeid\s*=\s*'([^']+)'", text)
            is_challenge = bool(m) and ("lvb.rsso2.com" in text or len(text) < 8000)
            if is_challenge:
                self._safe = m.group(1)          # _safe 值就是 safeid 本身
                continue                          # 带 cookie 重试
            return body
        return b""

    def _get_text(self, url, referer=None):
        return self._fetch(url, referer).decode("utf-8", "ignore")

    # ─────────── 解析 ───────────
    _CARD_RE = re.compile(
        r'<a href="(https://bav53\.cc/video/(\d+)/[^"]*/)"\s+title="([^"]*)"(.*?)</a>', re.S)

    def _parse_cards(self, html):
        """解析视频卡片 -> [{vod_id(完整URL), vod_name, vod_pic, vod_remarks}]，去重保序"""
        out, seen = [], set()
        for m in self._CARD_RE.finditer(html):
            url, vid, title, block = m.group(1), m.group(2), m.group(3), m.group(4)
            if vid in seen:
                continue
            seen.add(vid)
            pic = ""
            pm = re.search(r'data-original="([^"]+)"', block)
            if pm:
                pic = pm.group(1)
            remarks = ""
            cm = re.search(r'class="item\s+([^"]+)"', block)
            cls = (cm.group(1) if cm else "").strip()
            if "premium" in cls:
                remarks = "VIP"
            elif "private" in cls:
                remarks = "免费"
            title = re.sub(r"\s+", " ", title).strip()
            out.append({"vod_id": url, "vod_name": title,
                        "vod_pic": pic, "vod_remarks": remarks})
        return out

    def _parse_page_count(self, html):
        """从分页提取最大页码（"最后"链接），失败返回 1"""
        m = re.search(r'class="last"[^>]*href="[^"]*?/(\d+)/"', html)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        nums = re.findall(r'class="page"[^>]*href="[^"]*?/(\d+)/"', html)
        if nums:
            try:
                return max(int(n) for n in nums)
            except Exception:
                pass
        return 1

    @staticmethod
    def _vid_from(vid):
        """从任意形态的 id/URL 提取纯数字视频 ID"""
        m = re.search(r"video/(\d+)/", str(vid))
        if not m:
            m = re.search(r"(\d+)", str(vid))
        return m.group(1) if m else ""

    # ─────────── 生命周期 ───────────
    def getDependence(self):
        return []

    def init(self, extend=""):
        if not isinstance(extend, str):
            extend = ""
        self.extend = extend
        self._http_init()

    def destroy(self):
        pass

    # ─────────── 首页 ───────────
    def homeContent(self, filter=None):
        classes = self._get_classes()
        return {"class": classes, "filters": {}, "list": self._home_videos()}

    def homeVideoContent(self):
        return {"list": self._home_videos()}

    def _home_videos(self):
        html = self._get_text(SITE + "/")
        vlist = self._parse_cards(html)
        if not vlist:
            html = self._get_text(SITE + "/new/")
            vlist = self._parse_cards(html)
        return vlist[:40]

    def _get_classes(self):
        html = self._get_text(SITE + "/categories/")
        classes, seen = [], set()
        for m in re.finditer(
                r'<a[^>]*href="https://bav53\.cc/categories/([^"/]+)/"[^>]*title="([^"]+)"', html):
            slug, name = m.group(1), m.group(2).strip()
            if slug in seen:
                continue
            seen.add(slug)
            classes.append({"type_id": slug, "type_name": name})
        if not classes:
            classes = [{"type_id": "new", "type_name": "最新"},
                       {"type_id": "amateur", "type_name": "Amateur"}]
        return classes

    # ─────────── 分类 ───────────
    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except Exception:
            page = 1
        tid = str(tid)
        if tid.startswith("http"):
            m = re.search(r"categories/([^/]+)/", tid)
            tid = m.group(1) if m else tid
        base = SITE + "/categories/" + tid
        url = base + "/" if page <= 1 else "%s/%d/" % (base, page)
        html = self._get_text(url)
        vlist = self._parse_cards(html)
        pagecount = self._parse_page_count(html)
        return {"list": vlist, "page": page, "pagecount": pagecount,
                "limit": 24, "total": len(vlist) * pagecount}

    # ─────────── 详情 ───────────
    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)):
            raw = str(ids[0])
        else:
            raw = str(ids)
        # ids 可能是完整 URL（含 slug）或纯数字
        m = re.search(r"(https://bav53\.cc/video/\d+/[^/]*/)", raw)
        if m:
            url = m.group(1)
        else:
            vid = self._vid_from(raw)
            if not vid:
                return {"list": []}
            url = "%s/video/%s/" % (SITE, vid)
        html = self._get_text(url)
        vod = {
            "vod_id": url,
            "vod_name": "",
            "vod_pic": "",
            "vod_content": "",
            "vod_year": "",
            "vod_remarks": "",
            "vod_play_from": "爱微",
            # 播放地址用详情页 URL：playerContent 实时解析（m3u8 token 有时效，不能缓存）
            "vod_play_url": "爱微社区$" + url,
        }
        hm = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if hm:
            vod["vod_name"] = re.sub(r"<[^>]+>|\s+", " ", hm.group(1)).strip()
        om = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if om:
            vod["vod_pic"] = om.group(1)
        dm = re.search(r'<meta property="og:description" content="([^"]*)"', html)
        if dm:
            vod["vod_content"] = dm.group(1).strip()
        ym = re.search(r'<meta property="og:video:release_date" content="([^"]+)"', html)
        if ym:
            vod["vod_year"] = ym.group(1)[:4]
        # 校验页面是否真的是请求的视频（无 slug 时服务端可能回退到随机视频）
        if "video/" in url:
            req_id = self._vid_from(url)
            ogm = re.search(r'<meta property="og:url" content="[^"]*video/(\d+)/', html)
            if ogm and ogm.group(1) != req_id:
                # 回退页：尝试用搜索找真实 slug
                alt = self._find_real_url(req_id)
                if alt:
                    return self.detailContent([alt])
                return {"list": []}
        if not vod["vod_name"]:
            vod["vod_name"] = "视频%s" % self._vid_from(url)
        return {"list": [vod]}

    def _find_real_url(self, vid):
        """用搜索找数字 ID 对应的真实详情页 URL（含 slug）"""
        html = self._get_text("%s/search/%s/videos/" % (SITE, vid))
        for m in self._CARD_RE.finditer(html):
            u = m.group(1)
            if "/video/%s/" % vid in u:
                return u
        return ""

    # ─────────── 搜索 ───────────
    def searchContent(self, key, quick=False, pg="1"):
        try:
            page = int(pg) if str(pg).isdigit() else 1
        except Exception:
            page = 1
        kw = urlparse.quote(str(key))
        base = "%s/search/%s/videos" % (SITE, kw)
        url = base + "/" if page <= 1 else "%s/%d/" % (base, page)
        html = self._get_text(url)
        vlist = self._parse_cards(html)
        return {"list": vlist}

    # ─────────── 播放（实时解析，token 保鲜）───────────
    def _get_play_lines(self, detail_url):
        """抓详情页 CSRF -> spped.php -> 多线路 m3u8。返回 [(key,name,url)]"""
        html = self._get_text(detail_url)
        cm = re.search(r'var PLAYER_CSRF = "([^"]+)"', html)
        if not cm:
            return []
        csrf = cm.group(1)
        api = "%s/player/spped.php?csrf=%s" % (SITE, csrf)
        body = self._fetch(api, referer=detail_url)
        try:
            data = json.loads(body.decode("utf-8", "ignore"))
        except Exception:
            return []
        lines = []
        for src in data.get("sources", []) or []:
            u = src.get("url", "")
            if u:
                lines.append((src.get("key", ""), src.get("name", ""), u))
        return lines

    def playerContent(self, flag, ids, vipFlags=None):
        raw = str(ids)
        m = re.search(r"(https://bav53\.cc/video/\d+/[^/]*/)", raw)
        if m:
            detail_url = m.group(1)
        else:
            vid = self._vid_from(raw)
            detail_url = "%s/video/%s/" % (SITE, vid) if vid else raw
        lines = self._get_play_lines(detail_url)
        if not lines:
            # VIP 视频未登录：详情页无播放器 -> 降级到 newembed 的 30s 预览 mp4
            vid = self._vid_from(detail_url)
            prev = self._get_preview_url(vid)
            if prev:
                return {"parse": 0, "url": prev,
                        "header": {"User-Agent": UA, "Referer": SITE + "/"},
                        "format": "video/mp4"}
            return {"parse": 0, "url": raw,
                    "header": {"User-Agent": UA, "Referer": SITE + "/"}}
        target = str(flag)
        picked = None
        for key, name, u in lines:
            if target and (target == key or target == name):
                picked = (key, name, u)
                break
        if not picked:
            picked = lines[0]
        _key, _name, m3u8 = picked
        return {
            "parse": 0,
            "url": m3u8,
            "header": {"User-Agent": UA, "Referer": SITE + "/"},
            "format": "application/x-mpegURL",
        }

    def _get_preview_url(self, vid):
        """newembed 页的预览 mp4（VIP 视频未登录只有这个，约 30s）"""
        if not vid:
            return ""
        html = self._get_text("%s/newembed/%s" % (SITE, vid))
        m = re.search(r'<source\s+src="([^"]+)"', html)
        return m.group(1) if m else ""

    # ─────────── 本地代理（兜底）───────────
    def localProxy(self, param):
        if isinstance(param, str):
            try:
                param = json.loads(param)
            except Exception:
                param = {}
        url = (param or {}).get("url", "")
        if not url:
            return [404, "text/plain", b"", {}]
        body = self._fetch(url)
        mime = "image/jpeg"
        if body[:4] == b"\x47\x40\x11\x10":
            mime = "video/mp2t"
        return [200, mime, body, {"User-Agent": UA}]

    # ─────────── WebView 嗅探 ───────────
    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        u = str(url).lower()
        return any(u.endswith(ext) for ext in (".m3u8", ".mp4", ".flv", ".ts", ".mkv", ".m4s"))

    def action(self, action):
        return json.dumps({"code": 0, "msg": "ok"}, ensure_ascii=False)

    def getName(self):
        return self.name


# ─────────── 本地自测（模拟壳调用链）───────────
if __name__ == "__main__":
    sp = Spider()
    sp.init("")
    print("== homeContent ==")
    hc = sp.homeContent(True)
    print("classes:", len(hc.get("class", [])), "| list:", len(hc.get("list", [])))
    for c in hc.get("class", [])[:5]:
        print("  ", c)
    if hc.get("list"):
        print("  sample:", hc["list"][0])
    print("== homeVideoContent ==")
    print("list:", len(sp.homeVideoContent().get("list", [])))
    print("== categoryContent ==")
    cc = sp.categoryContent("solowork", "1", False, {})
    print("list:", len(cc.get("list", [])), "| pagecount:", cc.get("pagecount"))
    if cc.get("list"):
        print("  sample:", cc["list"][0])
    print("== detailContent ==")
    dc = sp.detailContent([hc["list"][0]["vod_id"]]) if hc.get("list") else sp.detailContent(["129377"])
    vod = dc["list"][0]
    print("  name:", vod["vod_name"][:50])
    print("  pic:", vod["vod_pic"][:80])
    print("  play:", vod["vod_play_from"], "|", vod["vod_play_url"][:70])
    print("== playerContent ==")
    pc = sp.playerContent("爱微", vod["vod_play_url"].split("$")[1])
    print("  url:", pc["url"][:110])
    print("  format:", pc.get("format"))
    print("  header keys:", list(pc.get("header", {}).keys()))
    print("== searchContent ==")
    sc = sp.searchContent("fc2", False, "1")
    print("list:", len(sc.get("list", [])))
