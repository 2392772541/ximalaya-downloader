# -*- coding: utf-8 -*-
"""
喜马拉雅音频免鉴权下载工具 (Ximalaya Downloader)
支持：单曲网页链接、手机分享链接、声音ID、包含链接的分享文本
默认下载：MP3 格式
"""
import sys
import os
import re
import time
import json
import ssl
import shutil
import subprocess
import urllib.request
import argparse

# 控制台编码自适应 (Windows 下优先 UTF-8)
if sys.platform.startswith("win"):
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 禁用全局严格 SSL 校验，防止部分未装系统根证书的裸机 Windows 报错
try:
    ssl_context = ssl._create_unverified_context()
except AttributeError:
    ssl_context = None

def get_app_dir():
    """获取程序所在目录（支持 PyInstaller 打包后的路径）"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def sanitize_filename(name):
    """过滤 Windows 文件名非法字符"""
    for c in ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]:
        name = name.replace(c, "_")
    return name.strip()

def extract_track_id(text):
    """从输入的文本、URL 或纯数字中提取喜马拉雅声音 ID"""
    text = str(text).strip()
    
    match = re.search(r'/sound/(\d+)', text)
    if match:
        return match.group(1)
        
    match = re.search(r'trackId=(\d+)', text, re.IGNORECASE)
    if match:
        return match.group(1)
        
    match = re.search(r'^\d+$', text)
    if match:
        return match.group(0)
        
    match = re.search(r'(\d{7,12})', text)
    if match:
        return match.group(1)
        
    return None

def get_track_info(track_id):
    """
    优先通过 mobile baseInfo 接口获取原生 MP3 直链，
    次选移动端 H5 tracks JSON 接口。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
    }

    # 策略 1 (首选 MP3 专用接口): mobile.ximalaya.com baseInfo
    # 该接口原生返回腾讯云 CDN 的 playUrl64/playUrl32，直接为标准 MP3 格式
    try:
        url_base = f"https://mobile.ximalaya.com/v1/track/baseInfo?trackId={track_id}"
        req1 = urllib.request.Request(url_base, headers=headers)
        with urllib.request.urlopen(req1, context=ssl_context, timeout=12) as resp:
            b_data = json.loads(resp.read().decode("utf-8"))
            if b_data and "title" in b_data:
                # 优先获取 MP3 链接
                audio_url = b_data.get("playUrl64") or b_data.get("playUrl32") or b_data.get("downloadUrl")
                if not audio_url:
                    audio_url = b_data.get("playPathAacv164") or b_data.get("playPathAacv224")

                if audio_url:
                    # 替换为安全 HTTPS 传输
                    if audio_url.startswith("http://"):
                        audio_url = "https://" + audio_url[7:]

                    return {
                        "track_id": track_id,
                        "title": b_data.get("title") or f"track_{track_id}",
                        "nickname": b_data.get("userInfo", {}).get("nickname") or "未知播客",
                        "album_title": b_data.get("albumTitle") or "",
                        "duration": b_data.get("duration") or 0,
                        "is_paid": b_data.get("isPaid", False),
                        "audio_url": audio_url,
                        "cover_url": b_data.get("coverLarge") or b_data.get("coverSmall")
                    }
    except Exception:
        pass

    # 策略 2 (备选接口): 移动端 H5 tracks JSON 接口
    try:
        url_h5 = f"https://m.ximalaya.com/tracks/{track_id}.json"
        req2 = urllib.request.Request(url_h5, headers=headers)
        with urllib.request.urlopen(req2, context=ssl_context, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and "title" in data:
                audio_url = data.get("play_path_64") or data.get("play_path_32") or data.get("play_path")
                if audio_url and audio_url.startswith("http://"):
                    audio_url = "https://" + audio_url[7:]

                return {
                    "track_id": track_id,
                    "title": data.get("title") or f"track_{track_id}",
                    "nickname": data.get("nickname") or "未知播客",
                    "album_title": data.get("album_title") or "",
                    "duration": data.get("duration") or 0,
                    "is_paid": data.get("is_paid", False),
                    "audio_url": audio_url,
                    "cover_url": data.get("cover_url") or data.get("cover_url_142")
                }
    except Exception:
        pass

    return None

def download_file(url, out_path):
    """流式下载音频文件并展示动态进度条与实时速度"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ssl_context) as resp:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 64
        start_time = time.time()
        last_update_time = 0

        with open(out_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                now = time.time()
                if now - last_update_time > 0.08 or downloaded == total_size:
                    last_update_time = now
                    elapsed = max(now - start_time, 0.001)
                    speed_mb = (downloaded / (1024 * 1024)) / elapsed

                    if total_size > 0:
                        pct = downloaded / total_size * 100
                        mb_c = downloaded / (1024 * 1024)
                        mb_t = total_size / (1024 * 1024)
                        bar_len = 25
                        filled = int(bar_len * downloaded // total_size)
                        bar = "=" * filled + ">" if filled < bar_len else "=" * bar_len
                        sys.stdout.write(f"\r  [{bar:<25}] {pct:5.1f}% ({mb_c:.1f}MB / {mb_t:.1f}MB) {speed_mb:.1f}MB/s")
                    else:
                        sys.stdout.write(f"\r  已下载: {downloaded / 1024 / 1024:.2f}MB ({speed_mb:.1f}MB/s)")
                    sys.stdout.flush()
    print()

def convert_m4a_to_mp3(m4a_path, mp3_path):
    """如果下载到的是 m4a 且本机有 ffmpeg，自动无缝转码为 mp3"""
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return False
    try:
        cmd = [ffmpeg_bin, "-y", "-v", "error", "-i", m4a_path, "-acodec", "libmp3lame", "-q:a", "2", mp3_path]
        subprocess.run(cmd, check=True)
        if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:
            os.remove(m4a_path)
            return True
    except Exception:
        pass
    return False

def process_download(url_or_id, output_dir):
    """解析并下载音频，确保最终产物为 MP3 格式"""
    track_id = extract_track_id(url_or_id)
    if not track_id:
        print(f"\n[错误] 无法从输入的文本中识别声音 ID: '{url_or_id}'")
        print("       支持格式例如: https://www.ximalaya.com/sound/1011055746 或直接输入 1011055746")
        return False

    print(f"\n[1/3] 正在解析声音 ID: {track_id} ...")
    info = get_track_info(track_id)
    if not info:
        print("[错误] 解析失败，请检查网络或声音 ID（该音频可能已下架或为私密内容）。")
        return False

    mins = info["duration"] // 60
    secs = info["duration"] % 60
    print(f"  - 声音标题: {info['title']}")
    print(f"  - 主播/播客: {info['nickname']}")
    if info["album_title"]:
        print(f"  - 所属专辑: {info['album_title']}")
    print(f"  - 音频时长: {info['duration']} 秒 ({mins}分{secs}秒)")

    if info.get("is_paid"):
        print("  * 提示: 该音频标记为付费/VIP内容，未购买可能仅返回试听片段。")

    audio_url = info.get("audio_url")
    if not audio_url:
        print("[错误] 未找到可直接下载的音频流直链。")
        return False

    os.makedirs(output_dir, exist_ok=True)
    raw_ext = os.path.splitext(audio_url.split("?")[0])[-1].lower() or ".mp3"
    
    # 目标文件名一律设为 .mp3
    target_filename = sanitize_filename(f"{info['title']} [{track_id}].mp3")
    final_mp3_path = os.path.join(output_dir, target_filename)

    print(f"\n[2/3] 准备下载音频流 ...")
    print(f"  - 直链地址: {audio_url}")
    print(f"  - 目标格式: MP3")
    print(f"  - 保存位置: {final_mp3_path}")

    print(f"\n[3/3] 开始下载 ...")
    try:
        if raw_ext == ".mp3":
            # 原生 MP3 直链，直接流式下载
            download_file(audio_url, final_mp3_path)
        else:
            # 临时下载为原始格式并尝试转为 MP3
            temp_path = os.path.join(output_dir, sanitize_filename(f"{info['title']} [{track_id}]_temp{raw_ext}"))
            download_file(audio_url, temp_path)
            if convert_m4a_to_mp3(temp_path, final_mp3_path):
                print("  [转换] 已自动转换为 MP3 格式。")
            else:
                # 若无 ffmpeg 则直接重命名为目标文件名
                if os.path.exists(temp_path):
                    shutil.move(temp_path, final_mp3_path)

        size_mb = os.path.getsize(final_mp3_path) / (1024 * 1024)
        print(f"\n[成功] 下载完成！文件大小: {size_mb:.2f} MB")
        print(f"       已保存为 MP3 文件: {final_mp3_path}\n")
        return True
    except Exception as e:
        print(f"\n[失败] 下载异常: {e}\n")
        return False

def interactive_mode(output_dir):
    """交互模式（双击 EXE 启动）"""
    print("=" * 66)
    print("      喜马拉雅音频免鉴权下载工具 (Ximalaya Downloader) - MP3版")
    print("=" * 66)
    print(f"默认输出格式: MP3 音频")
    print(f"默认保存目录: {output_dir}")
    print("使用方式:")
    print("  1. 复制喜马拉雅网页链接 (例如 https://www.ximalaya.com/sound/1011055746)")
    print("  2. 或者直接输入声音 ID (例如 1011055746)")
    print("  3. 支持随时粘贴新的链接继续下载")
    print("  4. 输入 q 或 exit 退出程序")
    print("=" * 66)

    while True:
        try:
            user_input = input("\n请输入链接或声音ID > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n程序已退出。")
            break

        if not user_input:
            continue
        if user_input.lower() in ["q", "quit", "exit"]:
            print("感谢使用，再见！")
            break

        process_download(user_input, output_dir)

def main():
    default_dir = os.path.join(get_app_dir(), "downloads")

    parser = argparse.ArgumentParser(description="喜马拉雅音频免鉴权下载工具 (输出MP3)")
    parser.add_argument("url_or_id", nargs="?", default=None, help="喜马拉雅单曲网页URL或纯数字声音ID")
    parser.add_argument("-o", "--output-dir", default=default_dir, help=f"保存目录，默认为: {default_dir}")
    args = parser.parse_args()

    out_dir = os.path.abspath(args.output_dir)

    if args.url_or_id:
        success = process_download(args.url_or_id, out_dir)
        sys.exit(0 if success else 1)
    else:
        interactive_mode(out_dir)

if __name__ == "__main__":
    is_interactive = not sys.argv[1:]
    try:
        main()
    except Exception as e:
        print(f"\n[致命异常] 程序运行错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if is_interactive:
            try:
                input("\n按回车键退出程序...")
            except Exception:
                pass
