from django.db import models

class Video(models.Model):
    video_file = models.FileField(upload_to='videos/')  # Videoları kaydetmek için.
    uploaded_at = models.DateTimeField(auto_now_add=True)  # Yüklenme tarihi.
    subtitle_file = models.FileField(upload_to='subtitles/', null=True, blank=True)  # Altyazı dosyası.
    output_video = models.FileField(upload_to='outputs/', null=True, blank=True)  # Altyazılı video dosyası.

    def __str__(self):
        return f"Video {self.id} - {self.video_file.name}"
