# -*- coding: utf-8 -*-
import sys, re, json
from urllib.parse import quote, unquote
sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def __init__(self): pass

class Spider(Spider):
    def init(self, extend=''):
        self.hdr = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://javhd.com/en/'
        }

    def _get(self, url, jsonmode=False, html=False):
        hdr = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8' if html else 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        if not html:
            hdr.update({'X-Requested-With': 'XMLHttpRequest'})
        try:
            import urllib.parse as up
            url = up.quote(url, safe=':/?=&%.-_#')
        except:
            pass
        for _ in range(4):
            try:
                import requests
                r = requests.get(url, headers=hdr, timeout=20)
                txt = r.text
            except:
                try:
                    import urllib.request
                    req = urllib.request.Request(url, headers=hdr)
                    txt = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='ignore')
                except:
                    return '' if not jsonmode else {}
            # 处理 meta refresh 跳转
            m = re.search(r'<meta\s+http-equiv="refresh"\s+content="0;url=\'([^\']+)\'"', txt, re.IGNORECASE)
            if not m:
                m = re.search(r'<meta\s+http-equiv="refresh"\s+content="[^"]*url=([^"]+)"', txt, re.IGNORECASE)
            if m:
                new_url = m.group(1).strip().strip("'")
                if new_url.startswith('http'):
                    url = new_url
                else:
                    url = 'https://javhd.com' + new_url
                continue
            if jsonmode:
                try:
                    return json.loads(txt)
                except:
                    # 尝试从 JSONP 或脚本标签中提取 JSON
                    json_match = re.search(r'({[\s\S]*})', txt)
                    if json_match:
                        try:
                            return json.loads(json_match.group(1))
                        except:
                            pass
                    return {}
            return txt
        return {} if jsonmode else ''

    def _cards(self, t):
        out = []
        # 支持多种卡片格式
        patterns = [
            r'<thumb-component\s+type-thumb="video"\s+(?:item-id="\d+"\s+)?video-id="(\d+)"\s+link-content="([^"]+)"\s+url-thumb="([^"]+)"\s+video-preview="([^"]*)"(?:\s+has-label="([^"]*)")?\s+title="([^"]+)"',
            r'data-video-id="(\d+)"[^>]*data-link="([^"]+)"[^>]*data-thumb="([^"]+)"[^>]*data-preview="([^"]*)"[^>]*data-label="([^"]*)"[^>]*title="([^"]+)"',
            r'video-id="(\d+)"[^>]*link-content="([^"]+)"[^>]*url-thumb="([^"]+)"[^>]*video-preview="([^"]*)"[^>]*title="([^"]+)"',
        ]
        for pattern in patterns:
            for c in re.findall(pattern, t):
                if len(c) >= 5:
                    vid = c[0]
                    link = c[1] if c[1].startswith('http') else 'https://javhd.com' + c[1]
                    pic = c[2] if c[2].startswith('http') else 'https://javhd.com' + c[2]
                    preview = c[3] if c[3].startswith('http') else ('https://javhd.com' + c[3] if c[3] else '')
                    label = c[4] if len(c) > 4 and c[4] else 'free'
                    title = c[5] if len(c) > 5 else (c[4] if len(c) > 4 else '')
                    out.append({'vid': vid, 'link': link, 'pic': pic, 'preview': preview, 'label': label, 'title': title})
        return out

    def _pic(self, th):
        if isinstance(th, dict):
            for k in ('1130x706', '940x530', '468x264', '374x233', 'original', 'large', 'medium'):
                if th.get(k):
                    return th[k]
            return next(iter(th.values()), '')
        return str(th) if th else ''

    def homeContent(self, filter=False):
        # 常见分类，可根据网站实际结构调整
        classes = [
            {'type_id': 'justadded', 'type_name': '最新'},
            {'type_id': 'popular', 'type_name': '热门'},
            {'type_id': 'top', 'type_name': '最多播放'},
            {'type_id': 'trending', 'type_name': '趋势'},
            {'type_id': 'upcoming', 'type_name': '即将推出'},
            {'type_id': 'categories', 'type_name': '全部分类'},
        ]
        return {'class': classes, 'list': self.homeVideoContent()}

    def homeVideoContent(self):
        try:
            j = self._get('https://javhd.com/en/api/content_block?block=custom&pgid=1339887660&isCasting=1&count=24&offset=0&castingPosition=8', True)
            out = []
            template = j.get('template', []) if isinstance(j, dict) else []
            for i in template:
                if isinstance(i, dict) and i.get('id'):
                    studio_url = i.get('studioUrl', '') or i.get('url', '') or i.get('link', '')
                    if studio_url and not studio_url.startswith('http'):
                        studio_url = 'https://javhd.com' + studio_url
                    out.append({
                        'vod_id': studio_url or str(i.get('id', '')),
                        'vod_name': i.get('title', '') or i.get('name', ''),
                        'vod_pic': self._pic(i.get('thumbs')),
                        'vod_remarks': i.get('label', '') or i.get('status', '')
                    })
            return out
        except Exception as e:
            return []

    def categoryContent(self, tid, pg='1', filter=False, extend={}):
        try:
            pg = int(pg) if str(pg).isdigit() else 1
        except:
            pg = 1
        
        # 支持传入完整 URL 或分类 ID
        if tid.startswith('http'):
            url = tid
            if '?' in url:
                url += f'&page={pg}'
            else:
                url += f'?page={pg}'
        else:
            # 标准分类 URL 格式
            url = f'https://javhd.com/en/japanese-porn-videos/{tid}/all/{pg}'
        
        j = self._get(url, True)
        
        # 如果 JSON 解析失败，尝试从 HTML 中解析
        if not j or (isinstance(j, dict) and not j.get('template')):
            html = self._get(url, html=True)
            if html:
                items = self._cards(html)
                # 尝试从 HTML 中提取总数
                total_match = re.search(r'results_count["\']?\s*[:=]\s*(\d+)', html)
                total = int(total_match.group(1)) if total_match else len(items)
                per_page = 24
                pc = max(1, (total + per_page - 1) // per_page)
                return {
                    'list': [{
                        'vod_id': i['link'],
                        'vod_name': i['title'],
                        'vod_pic': i['pic'],
                        'vod_remarks': 'VIP' if i['label'] != 'free' else '',
                        'vod_content': i['label']
                    } for i in items],
                    'page': pg,
                    'pagecount': pc,
                    'limit': per_page,
                    'total': total
                }
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 24, 'total': 0}
        
        items = self._cards(j.get('template', ''))
        import math
        total = j.get('results_count', 0)
        per_page = max(1, j.get('per_page', 24))
        pc = max(1, int(math.ceil(total / per_page)))
        
        return {
            'list': [{
                'vod_id': i['link'],
                'vod_name': i['title'],
                'vod_pic': i['pic'],
                'vod_remarks': 'VIP' if i['label'] != 'free' else '',
                'vod_content': i['label']
            } for i in items],
            'page': pg,
            'pagecount': pc,
            'limit': per_page,
            'total': total
        }

    def detailContent(self, ids):
        if not isinstance(ids, list):
            ids = [ids]
        u = ids[0]
        
        # 处理纯数字 ID
        if re.fullmatch(r'\d+', str(u)):
            u = f'https://javhd.com/en/id/{u}/'
        elif not str(u).startswith('http'):
            u = 'https://javhd.com' + str(u)
            
        h = self._get(u, html=True)
        if not h:
            return {'list': []}
        
        # 多种方式提取视频 ID
        cid = None
        patterns = [
            r'content-path="/en/player_api\?videoId=(\d+)&amp;is_trailer=\d+"',
            r'content-id="(\d+)"',
            r'videoId[=:]\s*["\']?(\d+)["\']?',
            r'data-video-id="(\d+)"',
            r'player_api\?videoId=(\d+)',
        ]
        for pattern in patterns:
            m = re.search(pattern, h)
            if m:
                cid = m.group(1)
                break
        
        if not cid:
            return {'list': []}
        
        # 提取标题
        t = re.search(r'<title>([^<]*)</title>', h)
        name = (t.group(1).split('|')[0].strip() if t else '')
        
        # 提取封面
        pic = ''
        p = re.search(r'--playerPoster:\s*url\(([^)]+)\)', h)
        if p:
            pic = p.group(1)
        else:
            p = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', h)
            if p:
                pic = p.group(1)
            else:
                p = re.search(r'poster=["\']?([^"\'>\s]+)', h)
                if p:
                    pic = p.group(1)
        
        # 提取描述
        d = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', h)
        desc = d.group(1) if d else ''
        
        # 提取标签/演员
        tags = []
        for tag_match in re.findall(r'<a[^>]*href="[^"]*/(?:tag|category|actress)/[^"]*"[^>]*>([^<]+)</a>', h):
            tags.append(tag_match.strip())
        
        return {
            'list': [{
                'vod_id': u,
                'vod_name': name,
                'vod_pic': pic,
                'vod_content': desc,
                'vod_actor': ','.join(tags[:3]) if tags else '',
                'vod_tag': ','.join(tags) if tags else '',
                'vod_play_from': 'javhd',
                'vod_play_url': f'完整版${u}|{cid}'
            }]
        }

    def searchContent(self, key, quick=False, pg='1'):
        try:
            pg = int(pg) if str(pg).isdigit() else 1
        except:
            pg = 1
            
        search_url = f'https://javhd.com/en/search?q={quote(key)}&page={pg}'
        j = self._get(search_url, True)
        
        if not j:
            # 尝试 HTML 模式
            h = self._get(search_url, html=True)
            if h:
                items = self._cards(h)
                return {
                    'list': [{
                        'vod_id': i['link'],
                        'vod_name': i['title'],
                        'vod_pic': i['pic'],
                        'vod_remarks': 'VIP' if i['label'] != 'free' else '',
                        'vod_content': i['label']
                    } for i in items]
                }
            return {'list': []}
            
        items = self._cards(j.get('template', ''))
        return {
            'list': [{
                'vod_id': i['link'],
                'vod_name': i['title'],
                'vod_pic': i['pic'],
                'vod_remarks': 'VIP' if i['label'] != 'free' else '',
                'vod_content': i['label']
            } for i in items]
        }

    def playerContent(self, flag, id, vipFlags):
        # 解析 id，可能是 "url|cid" 格式
        if '|' in id:
            original_url, cid = id.split('|', 1)
        else:
            cid = None
            # 从 URL 中提取 cid
            m = re.search(r'videoId[=:](\d+)', id)
            if m:
                cid = m.group(1)
            original_url = id
        
        if not cid:
            return {}
            
        api_url = f'https://javhd.com/en/player_api?videoId={cid}&is_trailer=0'
        j = self._get(api_url, True)
        
        if not j or not j.get('sources'):
            # 尝试获取预告片
            api_url = f'https://javhd.com/en/player_api?videoId={cid}&is_trailer=1'
            j = self._get(api_url, True)
            
        if not j or not j.get('sources'):
            return {}
            
        sources = j.get('sources', [])
        if not sources:
            return {}
            
        # 按分辨率排序，优先选择高清晰度
        try:
            s = sorted(sources, key=lambda x: int(x.get('res', 0) or 0), reverse=True)[0]
        except:
            s = sources[0]
            
        video_url = s.get('src', '')
        if video_url and not video_url.startswith('http'):
            video_url = 'https://javhd.com' + video_url
            
        # 判断是否需要解析（m3u8 通常不需要，mp4 直接播放）
        parse_flag = 0
        if video_url.endswith('.m3u8') or '.m3u8' in video_url:
            parse_flag = 0
        elif video_url.endswith('.mp4'):
            parse_flag = 0
            
        return {
            'parse': parse_flag,
            'url': video_url,
            'header': json.dumps({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://javhd.com/en/',
                'Origin': 'https://javhd.com'
            })
        }

    def localProxy(self, param):
        return []
