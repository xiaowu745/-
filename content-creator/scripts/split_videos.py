#!/usr/bin/env python3
"""
FFmpeg 批量视频切割脚本
将文件夹中的所有视频按指定时长自动切割成多个片段。

使用方法：
    python split_videos.py ./videos 5

参数：
    input_folder  - 包含视频文件的文件夹路径
    clip_duration - 每个片段的时长（秒），默认 5 秒
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# ============ 可调整的参数 ============
CLIP_DURATION = 5              # 每个片段的时长（秒）
INPUT_FOLDER = "./videos"      # 视频文件夹路径
OUTPUT_FOLDER = "./output_clips"  # 输出文件夹路径
MIN_TAIL_DURATION = 1.0        # 尾段最短保留时长（秒）
# =====================================

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm", ".flv", ".wmv"}


def get_video_duration(filepath: str) -> float:
    """使用 ffprobe 获取视频时长（秒）。"""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        filepath,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {filepath}\n{result.stderr}")
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def split_video(filepath: str, clip_duration: int, output_dir: str) -> list[str]:
    """将单个视频切割成多个片段，返回输出文件路径列表。"""
    duration = get_video_duration(filepath)
    stem = Path(filepath).stem
    ext = Path(filepath).suffix

    created_clips = []
    clip_index = 1
    start = 0.0

    while start < duration:
        remaining = duration - start
        is_tail = remaining < clip_duration

        # 尾段太短则跳过
        if is_tail and remaining < MIN_TAIL_DURATION:
            break

        if is_tail:
            tag = f"_clip{clip_index:03d}_tail"
        else:
            tag = f"_clip{clip_index:03d}"

        output_name = f"{stem}{tag}{ext}"
        output_path = os.path.join(output_dir, output_name)

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", f"{start:.3f}",
            "-i", filepath,
            "-t", f"{clip_duration:.3f}" if not is_tail else f"{remaining:.3f}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-avoid_negative_ts", "make_zero",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  [错误] 切割失败: {output_name}")
            print(f"         {result.stderr.splitlines()[-1] if result.stderr else '未知错误'}")
        else:
            created_clips.append(output_path)
            duration_label = f"{remaining:.1f}s (尾段)" if is_tail else f"{clip_duration}s"
            print(f"  [OK] {output_name}  ({duration_label})")

        start += clip_duration
        clip_index += 1

    return created_clips


def main():
    input_folder = sys.argv[1] if len(sys.argv) > 1 else INPUT_FOLDER
    clip_duration = int(sys.argv[2]) if len(sys.argv) > 2 else CLIP_DURATION
    output_folder = sys.argv[3] if len(sys.argv) > 3 else OUTPUT_FOLDER

    input_folder = os.path.abspath(input_folder)
    output_folder = os.path.abspath(output_folder)

    if not os.path.isdir(input_folder):
        print(f"错误: 输入文件夹不存在 -> {input_folder}")
        sys.exit(1)

    # 检查 ffmpeg 是否安装
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except FileNotFoundError:
        print("错误: 未找到 ffmpeg，请先安装 ffmpeg")
        sys.exit(1)

    # 收集视频文件
    videos = sorted(
        f for f in os.listdir(input_folder)
        if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not videos:
        print(f"未找到视频文件（支持格式: {', '.join(SUPPORTED_EXTENSIONS)}）")
        sys.exit(0)

    os.makedirs(output_folder, exist_ok=True)

    print(f"找到 {len(videos)} 个视频，每段 {clip_duration} 秒")
    print(f"输入: {input_folder}")
    print(f"输出: {output_folder}")
    print("-" * 50)

    total_clips = 0
    for i, filename in enumerate(videos, 1):
        filepath = os.path.join(input_folder, filename)
        duration = get_video_duration(filepath)
        print(f"\n[{i}/{len(videos)}] {filename} ({duration:.1f}s)")

        clips = split_video(filepath, clip_duration, output_folder)
        total_clips += len(clips)

    print("-" * 50)
    print(f"完成! {len(videos)} 个视频 -> {total_clips} 个片段")
    print(f"输出目录: {output_folder}")


if __name__ == "__main__":
    main()
