from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.tools.drawing import circle

video = VideoFileClip("D:/workspace/album_newnew/upload/video/" + "1004-2021-05-30.mp4").add_mask()

video_duration = video.duration
w, h = video.size

# 这里的mask是一个半径按照 r(t) = 800-200*t  根据时间变化消失的圆
video.mask.make_frame = lambda t: circle(screensize=(w, h), center=(w/2, h/4), radius=max(0, int(800 - 200 * t)), col1=1, col2=0, blur=4)
the_start = TextClip("2021-7-2日精彩瞬间", font="Arial", color="black", kerning=5, fontsize=150).set_duration(1)
# 搞一个TextClip来放The End
the_end = TextClip("The End", font="Arial", color="black", kerning=5, fontsize=150).set_duration(1)

final = CompositeVideoClip([the_start.set_pos('center').set_start(0), video, the_end.set_pos('center').set_start(video_duration-1)], size=video.size)

final.to_videofile("D:/workspace/album_newnew/upload/video/" + "temp" + ".mp4", fps=24, remove_temp=False)