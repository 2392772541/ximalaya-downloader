# -*- coding: utf-8 -*-
import sys, os, re, json, urllib.request, argparse

def sanitize_filename(name):
    for c in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(c, '_')
    return name.strip()

def extract_track_id(url_or_id):
    url_or_id = str(url_or_id).strip()
    match = re.search(r'/sound/(\d+)', url_or_id)
    if match: return match.group(1)
    match = re.search(r'trackId=(\d+)', url_or_id, re.IGNORECASE)
    if match: return match.group(1)
    match = re.search(r'^\d+$', url_or_id)
    if match: return match.group(0)
    match = re.search(r'(\d{7,12})', url_or_id)
    if match: return match.group(1)
    raise ValueError(f"无法识别声音ID: {url_or_id}")

def get_track_info(track_id):
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"}
    # 优先使用 baseInfo 获取原生 MP3
    try:
        url = f"https://mobile.ximalaya.com/v1/track/baseInfo?trackId={track_id}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and "title" in data:
                audio_url = data.get("playUrl64") or data.get("playUrl32") or data.get("downloadUrl")
                if audio_url and audio_url.startswith("http://"):
                    audio_url = "https://" + audio_url[7:]
                return {
                    "title": data.get("title") or f"track_{track_id}",
                    "nickname": data.get("userInfo", {}).get("nickname") or "",
                    "duration": data.get("duration") or 0,
                    "audio_url": audio_url
                }
    except Exception:
        pass
    # 备用 H5
    url = f"https://m.ximalaya.com/tracks/{track_id}.json"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        audio_url = data.get("play_path_64") or data.get("play_path_32") or data.get("play_path")
        if audio_url and audio_url.startswith("http://"):
            audio_url = "https://" + audio_url[7:]
        return {
            "title": data.get("title") or f"track_{track_id}",
            "nickname": data.get("nickname") or "",
            "duration": data.get("duration") or 0,
            "audio_url": audio_url
        }

def main():
    parser = argparse.ArgumentParser(description="喜马拉雅单曲快速下载为 MP3")
    parser.add_argument("url_or_id", help="喜马拉雅网页链接或声音ID")
    parser.add_argument("-o", "--output-dir", default=".", help="保存目录")
    args = parser.parse_args()

    track_id = extract_track_id(args.url_or_id)
    info = get_track_info(track_id)
    audio_url = info.get("audio_url")
    if not audio_url:
        print("未找到音频直链！")
        sys.exit(1)

    ext = ".mp3" if (".mp3" in audio_url) else (os.path.splitext(audio_url.split("?")[0])[-1] or ".mp3")
    filename = sanitize_filename(f"{info['title']} [{track_id}]{ext}")
    out_dir = os.path.abspath(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)

    print(f"正在下载: {info['title']}")
    print(f"音频直链: {audio_url}")
    print(f"保存路径: {out_path}")

    req = urllib.request.Request(audio_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(out_path, "wb") as f:
        f.write(resp.read())

    print(f"下载完成！大小: {os.path.getsize(out_path) / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()
