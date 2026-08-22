# -*- coding: utf-8 -*-
import sys
import re
import time
import base64
import threading
from urllib.parse import quote, unquote, parse_qs, urljoin
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def fetch(self, url, headers=None, **kw):
            import requests as rq
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r

HOSTS = ['1.92998cao.cc:8888', '1.92996cao.cc:8888', '1.92613cao.cc:8888', '1.92612cao.cc:8888']
UA = 'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36'
CATEGORIES = [
    {'type_id': '1', 'type_name': '大陆'}, {'type_id': '2', 'type_name': '日韩'},
    {'type_id': '3', 'type_name': '欧美'}, {'type_id': '4', 'type_name': '动漫'},
    {'type_id': '5', 'type_name': '综艺'}, {'type_id': '6', 'type_name': '国产传媒'},
    {'type_id': '7', 'type_name': '偷拍自拍'}, {'type_id': '9', 'type_name': '大陆杂类'},
    {'type_id': '10', 'type_name': '日韩无码'}, {'type_id': '11', 'type_name': '中文字幕'},
    {'type_id': '12', 'type_name': '日韩杂类'}, {'type_id': '19', 'type_name': '欧美无码'},
    {'type_id': '20', 'type_name': '黑白专区'}, {'type_id': '23', 'type_name': '少女动漫'},
    {'type_id': '24', 'type_name': '字幕动漫'}, {'type_id': '26', 'type_name': '3D动漫'},
    {'type_id': '30', 'type_name': '网爆黑料'}, {'type_id': '35', 'type_name': '绿帽偷情'},
    {'type_id': '36', 'type_name': 'JK萝莉'}, {'type_id': '37', 'type_name': '强奸迷奸'},
    {'type_id': '38', 'type_name': '网红主播'}, {'type_id': '39', 'type_name': '吃瓜黑料'},
    {'type_id': '40', 'type_name': '女优大厂'}, {'type_id': '41', 'type_name': '强奸迷奸二区'},
    {'type_id': '42', 'type_name': '偷拍街拍'}, {'type_id': '43', 'type_name': 'OL人妻'},
    {'type_id': '44', 'type_name': '肛交SM'}, {'type_id': '45', 'type_name': '大厂剧情'},
]
_PORT = 9988
_CACHE = {}
_LIST_CACHE = {}
_SEM = threading.Semaphore(6)
_PLACEHOLDER = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
_SESS = None
_IMG = None
_HOST_OK = None
_PROXY_ON = False


def _log(msg):
    try:
        import os
        with open('/sdcard/Download/就要草_diag.txt', 'a') as f:
            f.write('%s %s\n' % (time.strftime('%H:%M:%S'), msg))
    except Exception:
        pass


def _http_get(u, headers=None, timeout=12):
    global _SESS
    if _SESS is None:
        try:
            import requests as rq
            _SESS = rq.Session()
            _SESS.verify = False
        except Exception:
            _SESS = False
    if _SESS:
        try:
            r = _SESS.get(u, headers=headers or {}, timeout=timeout)
            _log('GET %d %s' % (r.status_code, u[:70]))
            return r
        except Exception as e:
            _log('GET ERR rq %s %s' % (type(e).__name__, u[:60]))
    try:
        import urllib.request
        import ssl
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(u, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read()
            r = type('R', (), {})()
            r.status_code = getattr(resp, 'status', 200)
            r.url = resp.geturl()
            r.content = body
            r.text = body.decode('utf-8', 'ignore')
            r.headers = {}
            _log('GET %d %s' % (r.status_code, u[:70]))
            return r
    except Exception as e:
        _log('GET ERR urllib %s %s' % (type(e).__name__, u[:60]))
        return None


def _uncode(html):
    m = re.search(r'document\.write\(decodeURIComponent\("([^"]+)"\)\)', html)
    return unquote(m.group(1)) if m else html


def _ent(s):
    return re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), s)


def _items(dec):
    vids = []
    for m in re.finditer(r'<div class="vod-item a-link" to="(/play/[^"]+)">.*?data-original="([^"]+)".*?<div class="rank-title">([^<]+)</div>', dec, re.S):
        vids.append({'vod_id': m.group(1).split('/')[-1], 'vod_name': _ent(m.group(3)), 'vod_pic': m.group(2), 'vod_remarks': ''})
    return vids


def _pagecount(dec, page):
    tm = re.search(r'font-weight:bold">/(\d+)</span>', dec)
    if tm:
        return int(tm.group(1))
    return page if 'vod-item' in dec else page - 1


def _pick_host():
    global _HOST_OK
    if _HOST_OK:
        return _HOST_OK
    for h in HOSTS:
        r = _http_get('https://%s/' % h, {'User-Agent': UA})
        if r and r.status_code == 200 and 'document.write' in r.text:
            _HOST_OK = h
            return h
    return HOSTS[0]


def _fetch_page(path):
    for h in ([_HOST_OK] if _HOST_OK else []) + HOSTS:
        r = _http_get('https://%s%s' % (h, path), {'User-Agent': UA})
        if not r or r.status_code != 200:
            continue
        if r.url.startswith('https://1.9254') or '最新地址发布页' in r.text[:500]:
            continue
        return h, _uncode(r.text)
    return '', ''


def _img_body(body):
    if body[:5] == b'<html' or body[:6] == b'<!DOCT':
        return None
    if b'\x00' not in body[:64] and len(body) > 64:
        try:
            raw = base64.b64decode(body + b'=' * (-len(body) % 4))
            if raw[:4] == b'RIFF' or raw[:2] == b'\xff\xd8' or raw[:8] == b'\x89PNG':
                return raw
        except Exception:
            pass
    return body


def _proxy_fetch(u):
    hit = _CACHE.get(u)
    if hit:
        return 200, hit[0], hit[1]
    for attempt in range(2):
        r = _http_get(u, {'User-Agent': UA, 'Referer': 'https://%s/' % _pick_host()}, timeout=15)
        if not r or r.status_code != 200:
            if attempt == 0:
                continue
            return 200, 'image/gif', _PLACEHOLDER
        body = r.content
        if body[:5] == b'<html':
            if attempt == 0:
                continue
            return 200, 'image/gif', _PLACEHOLDER
        body = _img_body(body)
        if body is None:
            return 200, 'image/gif', _PLACEHOLDER
        ct = 'image/jpeg'
        if body[:4] == b'RIFF' and body[8:12] == b'WEBP':
            global _IMG
            if _IMG is None:
                _IMG = 0
                try:
                    from PIL import Image
                    _IMG = Image
                except Exception:
                    _IMG = None
            if _IMG:
                try:
                    import io
                    im = _IMG.open(io.BytesIO(body)).convert('RGB')
                    out = io.BytesIO()
                    im.save(out, 'JPEG', quality=88)
                    body = out.getvalue()
                except Exception:
                    ct = 'image/webp'
            else:
                ct = 'image/webp'
        elif body[:2] == b'\xff\xd8':
            ct = 'image/jpeg'
        elif body[:8] == b'\x89PNG\r\n\x1a\n':
            ct = 'image/png'
        _CACHE[u] = (ct, body)
        if len(_CACHE) > 400:
            _CACHE.clear()
        return 200, ct, body
    return 200, 'image/gif', _PLACEHOLDER


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        q = parse_qs(self.path.split('?', 1)[1]) if '?' in self.path else {}
        u = unquote(q.get('url', [''])[0]) if q else ''
        if not u:
            self.send_response(404)
            self.end_headers()
            return
        status, ct, body = _proxy_fetch(u)
        self.send_response(status)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'public, max-age=86400')
        self.end_headers()
        if body:
            self.wfile.write(body)


def _start_proxy():
    global _PORT, _PROXY_ON
    if _PROXY_ON:
        return _PORT
    for port in range(9988, 9998):
        try:
            srv = ThreadingHTTPServer(('127.0.0.1', port), _Handler)
            srv.daemon_threads = True
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            _PORT = port
            _PROXY_ON = True
            return port
        except OSError:
            continue
    return 9988


def _pic(poster):
    if not poster:
        return ''
    _start_proxy()
    return 'http://127.0.0.1:%d/91c/pic?url=%s' % (_PORT, quote(poster, safe=''))


class Spider(Spider):
    def getName(self):
        return '就要草'

    def isVideoFormat(self, url):
        return bool(url and ('.m3u8' in url or '.mp4' in url))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return None

    def localProxy(self, param):
        p = param.split('//', 1)[1] if param.startswith('http') else param
        q = parse_qs(p.split('?', 1)[1]) if '?' in p else {}
        u = unquote(q.get('url', [''])[0]) if q else ''
        if not u:
            return [404, 'text/plain', '']
        status, ct, body = _proxy_fetch(u)
        return [status, ct, body]

    def init(self, extend=''):
        _pick_host()

    def homeContent(self, filter=False):
        return {'class': CATEGORIES, 'list': []}

    def homeVideoContent(self):
        h, dec = _fetch_page('/')
        vids, seen = [], set()
        for v in _items(dec):
            if v['vod_id'] not in seen:
                seen.add(v['vod_id'])
                v['vod_pic'] = _pic(v['vod_pic'])
                vids.append(v)
        return {'list': vids}

    def categoryContent(self, tid, pg=1, filter=False, extend=''):
        pg = max(int(str(pg)), 1)
        path = '/type/%s' % tid if pg == 1 else '/type/%s/%d/' % (tid, pg)
        h, dec = _fetch_page(path)
        vids = _items(dec)
        for v in vids:
            v['vod_pic'] = _pic(v['vod_pic'])
        pc = _pagecount(dec, pg)
        return {'list': vids, 'page': pg, 'pagecount': pc, 'limit': 9, 'total': pc * 9}

    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        vid = ids[0]
        h, dec = _fetch_page('/play/' + vid)
        tm = re.search(r'<div class="video-title">([^<]+)</div>', dec)
        name = _ent(tm.group(1)) if tm else vid
        um = re.search(r'var url = "([^"]+\.m3u8[^"]*)"', dec)
        url = um.group(1) if um else ''
        return {'list': [{'vod_id': vid, 'vod_name': name, 'vod_pic': '',
                          'vod_play_from': 'm3u8', 'vod_play_url': '%s$%s' % (name, url)}]}

    def searchContent(self, key, quick=False, pg='1'):
        h, dec = _fetch_page('/search/' + quote(key))
        vids = _items(dec)
        for v in vids:
            v['vod_pic'] = _pic(v['vod_pic'])
        return {'list': vids, 'page': pg, 'pagecount': 1, 'limit': 9, 'total': len(vids)}

    def playerContent(self, flag, id, vipFlags=None):
        return {'parse': 0, 'url': id}