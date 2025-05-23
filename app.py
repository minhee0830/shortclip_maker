import os
import uuid
import subprocess
from flask import Flask, render_template, request, send_file
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
EXPORT_FOLDER = 'exports'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

def force_convert_to_h264(input_path):
    output_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_converted_safe.mp4")
    command = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", input_path,
        "-preset", "ultrafast",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 변환 실패:\n{result.stderr.decode()}")
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("변환된 mp4 파일이 없습니다.")
    return output_path

def get_safe_clip(path):
    clip = VideoFileClip(path).without_audio()
    if clip.duration < 10:
        raise ValueError("영상 길이는 10초 이상이어야 합니다.")
    if clip.duration > 120:
        raise ValueError("영상은 최대 2분까지만 허용됩니다.")
    if clip.w > clip.h:
        raise ValueError("가로형 영상은 허용되지 않습니다. 세로형 영상만 가능합니다.")
    return clip.resize(height=1920)

def create_brand_title(brand_name, video_duration, video_size):
    return TextClip(
        brand_name,
        fontsize=60,
        font='NanumGothic',
        color='white',
    ).on_color(
        size=None,
        color=(0, 0, 0),
        col_opacity=0.6,
        pos='center',
        padding=(10, 30)
    ).set_position(('center', 140)).set_duration(video_duration)

def create_fixed_title(product_name, video_duration, video_size):
    return TextClip(
        product_name,
        fontsize=80,
        font='NanumGothic',
        color='white',
    ).on_color(
        size=None,
        color=(0, 0, 0),
        col_opacity=0.6,
        pos='center',
        padding=(15, 30)
    ).set_position(('center', 240)).set_duration(video_duration)

def generate_subtitle_clips(script, video_duration, video_size):
    lines = script.strip().split('\n')
    clips = []
    per_clip_duration = min(3, video_duration / len(lines))

    for i, line in enumerate(lines):
        txt_clip = TextClip(
            line,
            fontsize=60,
            font='NanumGothic',
            color='white',
        ).on_color(
            size=None,
            color=(0, 0, 0),
            col_opacity=0.6,
            pos='center',
            padding=(10, 20)
        ).set_position(('center', video_size[1] - 500)).set_start(i * per_clip_duration).set_duration(per_clip_duration)
        clips.append(txt_clip)

    return clips

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'video' not in request.files:
            return '동영상 파일이 없습니다.'
        video = request.files['video']
        script = request.form['script']
        brand_name = request.form['brand']
        product_name = request.form['product']

        input_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.mp4")
        video.save(input_path)

        converted_path = None

        try:
            converted_path = force_convert_to_h264(input_path)
            clip = get_safe_clip(converted_path)
            subtitles = generate_subtitle_clips(script, clip.duration, clip.size)
            product_clip = create_fixed_title(product_name, clip.duration, clip.size)
            brand_clip = create_brand_title(brand_name, clip.duration, clip.size)

            final = CompositeVideoClip([clip, brand_clip, product_clip] + subtitles)
            output_path = os.path.join(EXPORT_FOLDER, f"result_{uuid.uuid4()}.mp4")
            final.write_videofile(output_path, codec='libx264', audio_codec='aac', threads=1, logger=None)

            return send_file(output_path, as_attachment=True)
        except Exception as e:
            return f"\u274c 처리 중 오류 발생: 영상 열기 실패: {e}"
        finally:
            if os.path.exists(input_path): os.remove(input_path)
            if converted_path and os.path.exists(converted_path): os.remove(converted_path)

    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
