from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
from .forms import VideoUploadForm
from .models import Video
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
from pydub import AudioSegment
from pydub.utils import make_chunks
import speech_recognition as sr
import srt
from datetime import timedelta
import os

def extract_audio(video_path, output_audio_path):
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(output_audio_path)

def split_audio(audio_path, chunk_length_ms):
    audio = AudioSegment.from_file(audio_path)
    chunks = make_chunks(audio, chunk_length_ms)
    return chunks

def transcribe_audio_chunk(audio_chunk, recognizer):
    with sr.AudioFile(audio_chunk) as source:
        audio = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return ""

def create_srt(transcriptions, chunk_duration_ms):
    subtitles = []
    start_time = timedelta()
    chunk_duration = timedelta(milliseconds=chunk_duration_ms)

    for index, transcription in enumerate(transcriptions):
        if transcription.strip():
            end_time = start_time + chunk_duration
            subtitles.append(srt.Subtitle(index, start_time, end_time, transcription))
        start_time += chunk_duration

    return srt.compose(subtitles)

def add_subtitles_to_video(video_path, srt_path, output_path):
    video = VideoFileClip(video_path)

    # SRT dosyasını oku ve altyazıları videoya ekle
    from srt import parse
    with open(srt_path, "r") as f:
        subtitles = list(parse(f.read()))

    subtitle_clips = []
    for subtitle in subtitles:
        text = subtitle.content
        start = subtitle.start.total_seconds()
        end = subtitle.end.total_seconds()

        # Metin klibini oluştur
        text_clip = TextClip(
            text,
            fontsize=24,  # Yazı boyutu
            color='white',  # Yazı rengi
            bg_color='black',  # Arka plan rengi
            font="C:/Windows/Fonts/Arial"  # Font dosyasının tam yolu
        )
        text_clip = text_clip.set_position(("center", "bottom")).set_duration(end - start).set_start(start)
        subtitle_clips.append(text_clip)

    # Video ve altyazıları birleştir
    final_video = CompositeVideoClip([video, *subtitle_clips])
    final_video.write_videofile(output_path, codec="libx264")

def upload_video(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save()
            video_path = video.video_file.path  # Yüklenen video dosyasının tam yolu

            # Altyazı dosyası ve çıktı yolları oluştur
            srt_dir = os.path.join(settings.MEDIA_ROOT, 'subtitles')  # subtitles klasörünü oluşturmak için yol
            srt_path = os.path.join(srt_dir, f"{video.id}.srt")  # Altyazı dosyasının tam yolu
            output_video_path = os.path.join(settings.MEDIA_ROOT, 'outputs', f"output_{video.id}.mp4")  # Çıktı video yolu

            # Klasörlerin mevcut olup olmadığını kontrol et ve oluştur
            os.makedirs(srt_dir, exist_ok=True)  # subtitles klasörünü oluştur
            os.makedirs(os.path.dirname(output_video_path), exist_ok=True)  # outputs klasörünü oluştur

            # Ses çıkarma, altyazı oluşturma ve videoya ekleme işlemleri burada devam eder
            audio_path = f"temp_audio_{video.id}.wav"  # Geçici ses dosyasının adı
            extract_audio(video_path, audio_path)  # Videodan ses çıkarma işlemi
            chunk_length_ms = 10000
            audio_chunks = split_audio(audio_path, chunk_length_ms)
            recognizer = sr.Recognizer()
            transcriptions = []
            for i, chunk in enumerate(audio_chunks):
                chunk_path = f"chunk_{i}.wav"
                chunk.export(chunk_path, format="wav")
                transcription = transcribe_audio_chunk(chunk_path, recognizer)
                transcriptions.append(transcription)
                os.remove(chunk_path)
            subtitles = create_srt(transcriptions, chunk_length_ms)
            with open(srt_path, "w") as f:
                f.write(subtitles)
            os.remove(audio_path)

            # Videoya altyazı ekle
            add_subtitles_to_video(video_path, srt_path, output_video_path)

            # Modeli güncelle
            video.subtitle_file.name = srt_path.replace(settings.MEDIA_ROOT, '')  # Göreceli yolu kaydet
            video.output_video.name = output_video_path.replace(settings.MEDIA_ROOT, '')  # Göreceli yolu kaydet
            video.save()

            return HttpResponse(f"Altyazılı video hazır: <a href='{video.output_video.url}'>İndir</a>")

    else:
        form = VideoUploadForm()

    return render(request, 'upload.html', {'form': form})
