# -*- coding: utf-8 -*-
import sys
import os
import re
import json
import urllib.request
import argparse

def sanitize_filename(name):
    # filter illegal filename characters
    for c in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(c, '_')
    return name.strip()

def extract_track_id(url_or_id):
    url_or_id = str(url_or_id).strip()
    match = re.search(r'/sound/(\d+)', url_or_id)
    if match:
        return match.group(1)
    match = re.search(r'^\d+$', url_or_id)
    if match:
        return match.group(0)
    raise ValueError(f"无法从输入识别喜马拉雅声音ID: {url_or_id}")

def get_track_info(track_id):
    url = f"https://m.ximalaya.com/tracks/{track_id}.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    
    title = data.get("title") or f"track_{track_id}"
    nickname = data.get("nickname") or ""
    album_title = data.get("album_title") or ""
    duration = data.get("duration") or 0
    is_paid = data.get("is_paid", False)
    
    # 优先获取64k，其次32k
    audio_url = data.get("play_path_64") or data.get("play_path_32") or data.get("play_path")
    if not audio_url:
        try:
            backup_url = f"https://mobile.ximalaya.com/v1/track/baseInfo?trackId={track_id}"
            req2 = urllib.request.Request(backup_url, headers=headers)
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                b_data = json.loads(resp2.read().decode("utf-8"))
                audio_url = b_data.get("playUrl64") or b_data.get("playUrl32") or b_data.get("downloadUrl")
                if not title and b_data.get("title"):
                    title = b_data.get("title")
        except Exception:
            pass

    return {
        "track_id": track_id,
        "title": title,
        "nickname": nickname,
        "album_title": album_title,
        "duration": duration,
        "is_paid": is_paid,
        "audio_url": audio_url,
        "cover_url": data.get("cover_url") or data.get("cover_url_142")
    }

def download_file(url, out_path):
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 64
        with open(out_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = downloaded / total_size * 100
                    mb_c = downloaded / (1024 * 1024)
                    mb_t = total_size / (1024 * 1024)
                    sys.stdout.write(f"\r[下载进度] {pct:5.1f}% ({mb_c:.1f}MB / {mb_t:.1f}MB)")
                    sys.stdout.flush()
                else:
                    sys.stdout.write(f"\r[已下载] {downloaded / 1024 / 1024:.2f}MB")
                    sys.stdout.flush()
    print()

def main():
    parser = argparse.ArgumentParser(description="喜马拉雅音频免鉴权直链下载工具")
    parser.add_argument("url_or_id", help="喜马拉雅音频页面URL或单曲ID (如 1011055746)")
    parser.add_argument("-o", "--output-dir", default=".", help="保存目录，默认为当前目录")
    args = parser.parse_args()

    track_id = extract_track_id(args.url_or_id)
    print(f"正在解析声音 ID: {track_id}...")
    info = get_track_info(track_id)
    
    print(f"标题: {info['title']}")
    print(f"主播: {info['nickname']}")
    if info.get("album_title"):
        print(f"专辑: {info['album_title']}")
    mins = info["duration"] // 60
    secs = info["duration"] % 60
    print(f"时长: {info['duration']} 秒 ({mins}分{secs}秒)")
    
    if info.get("is_paid"):
        print("提示: 此音频标记为付费/VIP内容，可能仅返回试听片段。")

    audio_url = info.get("audio_url")
    if not audio_url:
        print("错误: 未找到可直接下载的音频流地址！")
        sys.exit(1)

    print(f"直链地址: {audio_url}")
    ext = os.path.splitext(audio_url.split("?")[0])[-1] or ".m4a"
    filename = sanitize_filename(f"{info['title']} [{track_id}]{ext}")
    out_dir = os.path.abspath(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)

    print(f"保存位置: {out_path}")
    download_file(audio_url, out_path)
    print(f"下载完成！文件大小: {os.path.getsize(out_path) / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()
