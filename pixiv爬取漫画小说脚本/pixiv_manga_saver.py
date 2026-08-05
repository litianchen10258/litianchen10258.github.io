import os, re, sys, requests
from datetime import datetime
from pathlib import Path

def log(msg):
    with open(Path(__file__).parent / '爬取日志.txt', 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

def extract_illust_id(url):
    m = re.search(r'pixiv\.net/(?:artworks|manga|i)/(\d+)', url)
    if not m:
        print('错误：无法从URL提取作品ID')
        sys.exit(1)
    return m.group(1)

def main():
    batch_mode = '--batch' in sys.argv

    if batch_mode:
        url_file = Path(__file__).parent / 'pixiv_manga_urls.txt'
        if not url_file.exists():
            print(f'批量模式需要创建 {url_file}，每行一个漫画URL')
            sys.exit(1)
        urls = [l.strip() for l in url_file.read_text(encoding='utf-8').splitlines() if l.strip()]
        if not urls:
            print('pixiv_manga_urls.txt 为空')
            sys.exit(1)
    elif len(sys.argv) < 2:
        print('用法: python pixiv_manga_saver.py <artwork_url>')
        print('       python pixiv_manga_saver.py --batch')
        sys.exit(1)
    else:
        urls = [sys.argv[1]]

    cookie_file = Path(__file__).parent / 'pixiv_cookies.txt'
    if not cookie_file.exists():
        print(f'请创建 {cookie_file}，放入你的Pixiv登录cookie（格式 PHPSESSID=xxx; 每行一个）')
        sys.exit(1)

    cookies = {}
    for line in cookie_file.read_text(encoding='utf-8').strip().splitlines():
        line = line.strip()
        if '=' in line:
            k, v = line.split('=', 1)
            cookies[k.strip()] = v.strip()

    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

    for url in urls:
        illust_id = extract_illust_id(url)
        print(f"\n--- 处理: {url} ---")
        download_manga(session, illust_id)

def download_manga(session, illust_id):
    log(f'漫画 {illust_id} 开始')
    print('获取作品信息...')
    info_url = f'https://www.pixiv.net/ajax/illust/{illust_id}'
    resp = session.get(info_url)
    info = resp.json()
    if info.get('error'):
        print(f"获取失败 (HTTP {resp.status_code}): {info.get('message', '')}")
        print('可能原因：① cookie 过期或无效 ② 作品ID错误 ③ 需要年龄验证')
        log(f'漫画 {illust_id} 失败: HTTP {resp.status_code}')
        return

    body = info['body']
    title = body.get('title', f'illust_{illust_id}')
    page_count = body.get('pageCount', 1)
    original_url = body.get('urls', {}).get('original', '')
    if not original_url:
        print('未找到原图URL')
        return

    ext = os.path.splitext(original_url.split('?')[0])[1] or '.jpg'
    safe_title = re.sub(r'[\\/:*?"<>|]', '', title).strip() or f'illust_{illust_id}'
    out_dir = Path(__file__).parent / f'{safe_title}_{illust_id}'
    out_dir.mkdir(exist_ok=True)

    print(f'共 {page_count} 页，保存到 {out_dir}')
    for page in range(page_count):
        if '_p0.' in original_url:
            page_url = original_url.replace('_p0.', f'_p{page}.')
        else:
            page_url = original_url
        local_name = f'p{page:02d}{ext}'
        r = session.get(page_url, headers={'Referer': 'https://www.pixiv.net/'})
        if r.ok:
            (out_dir / local_name).write_bytes(r.content)
            print(f'  下载: {local_name}')
        else:
            print(f'  {local_name} 下载失败 (HTTP {r.status_code})')

    log(f'漫画 {illust_id} 《{title}》成功 -> {out_dir}')
    print('完成! 保存至: ' + str(out_dir))

if __name__ == '__main__':
    main()
