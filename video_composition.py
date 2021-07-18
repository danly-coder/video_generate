from datetime import timedelta

import cv2
import glob
import pymysql
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify, app
# 引用 APSchedule
from flask_apscheduler import APScheduler
# 引用 congfig 配置
from config import Config
from moviepy.editor import *
from moviepy.editor import TextClip
from moviepy.video.tools.drawing import circle
import os
from flask_cors import *
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

app = Flask(__name__)


# # 设置静态文件缓存过期时间
# app.send_file_max_age_default = timedelta(seconds=1)

class Config(object):
    SCHEDULER_API_ENABLED = True
    JOBS = [
        {
            'id': 'job1',
            'func': '__main__:TimerMain',
            'args': '',
            'trigger': 'interval',
            'seconds': 86400

        }
    ]


# 接口执行
CORS(app, resources=r'/*')
@app.route('/wonderfulMomentGenerate', methods=['POST', 'GET'])  # 添加路由
def main():
    path = "D:/workspace/album_newnew/upload/"
    # path = "/home/photoAblum/resource/upload/"
    userid = request.args['userid']
    #单张图片合成视频
    userid_toVideo(path, userid)
    return "success"


# 定时执行
def TimerMain():
    path = "D:/workspace/album_newnew/upload/"
    # path = "/home/photoAblum/resource/upload/"
    # 将图片合成视频
    images_to_video(path)


# 将图片裁剪为一样大小
def resize(img_array, align_mode):
    _height = 640
    _width = 554

    for i in range(0, len(img_array)):
        img1 = cv2.resize(img_array[i], (_width, _height), interpolation=cv2.INTER_LINEAR)
        img_array[i] = img1

    return img_array, (_width, _height)


#定时生成视频
def images_to_video(path):
    print("查找数据库")
    img_array = []
    # 打开数据库连接
    db = pymysql.connect(host="127.0.0.1", user="root", password="123456", database="album")
    # 使用 cursor() 方法创建一个游标对象 cursor
    cursor = db.cursor()
    # 使用 execute()  方法执行 SQL 查询
    cursor.execute("SELECT id from user")
    # 获取所有用户ID
    ids = cursor.fetchall()
    for id in ids:
        # 获取该用户生成视频的最新时间
        sql = 'SELECT MAX(createTime) from jingcai where id=' + str(id[0])
        cursor.execute(sql)
        MaxCreateTime = cursor.fetchall()
        sql1 = ""
        # 如果最新时间不为空，
        if MaxCreateTime[0][0] != None:
            sql1 = 'SELECT  CONVERT(uploadTime,date) as date, count(name) as nameSum from photo WHERE userId = ' + str(
                id[0]) + ' GROUP BY date HAVING COUNT(*) >=5 and MAX(date) >="' + str(
                MaxCreateTime[0][0]) + '" ORDER BY date DESC'
        # 如果该用户还没生成视频
        else:
            sql1 = 'SELECT  CONVERT(uploadTime,date) as date, count(name) as nameSum from photo WHERE userId = ' + str(
                id[0]) + ' GROUP BY date HAVING COUNT(*) >=5 ORDER BY date DESC'
        print(sql1)
        cursor.execute(sql1)
        # 获取该用户下所有图片大于10张的日期和图片数量
        tenPhotos = cursor.fetchall()
        if tenPhotos != ():
            for tenPhoto in tenPhotos:
                sql2 = 'SELECT name from photo WHERE uploadTime LIKE "' + str(
                    tenPhoto[0]) + '%"' + ' and userId = ' + str(id[0])
                cursor.execute(sql2)
                # 获取该用户下图片最多日期下的图片
                photoNames = cursor.fetchall()
                interval = len(photoNames) // 40 + 1
                print(interval)
                img_array = []
                photoNamelistTemp = list(photoNames)
                photoNamelist = []
                for i in range(len(photoNamelistTemp)):
                    if i % interval == 0:
                        photoNamelist.append(photoNamelistTemp[i][0])
                # 遍历该用户、该天上传的所有图片
                print(photoNamelist)
                for i in range(len(photoNamelist)):
                    filename = path + "compress_img/" + photoNamelist[i] + '.jpg'
                    print(filename)
                    img = cv2.imread(filename)
                    if img is None:
                        print(filename + " is error!")
                        continue
                    img_array.append(img)
                # 图片的大小需要一致
                if img_array != []:
                    img_array, size = resize(img_array, 'lagerest')
                    fps = 1
                    smallvideoUrl = path + 'imgVideo/' + str(id[0]) + "-" + str(tenPhoto[0]) + "/"
                    if os.path.exists(smallvideoUrl) == 0:
                        os.mkdir(smallvideoUrl)
                    for i in range(len(img_array)):
                        #判断小视频是否存在
                        if os.path.exists(smallvideoUrl + photoNamelist[i] + '.avi'):
                            print("该视频已存在")
                            continue
                        cv2.imwrite(smallvideoUrl + photoNamelist[i] + '.jpg', img_array[i])
                        out = cv2.VideoWriter(smallvideoUrl + photoNamelist[i] + '.avi', cv2.VideoWriter_fourcc(*'DIVX'),
                                              fps, size)
                        out.write(img_array[i])
                        out.release()
                    # 将封面（第一张图片）保存起来
                    cv2.imwrite(path + "cover/" + "origin_" + photoNamelist[0] + '.jpg', img_array[0])
                    #将多个视频拼接,参数有根路径、userId、视频名称
                    videoName = str(id[0]) + "-" + str(tenPhoto[0])
                    print(videoName)
                    transitions_animation(path, videoName)
                    # 给视频添加背景
                    addmusic(path, videoName)
                    # 将制作的封面存入cover文件夹
                    coverFilename = path + "cover/" + "origin_" + photoNamelist[0] + '.jpg'
                    # 生成封面图片
                    generateCoverImg(coverFilename, path, videoName + ".jpg", str(tenPhoto[0]))
                    # 将生成的视频存入数据库
                    jingcaiSelectSql = 'SELECT * from jingcai WHERE id = ' + str(id[0]) + ' and createTime = "' + str(
                        tenPhoto[0]) + '"'
                    print(jingcaiSelectSql)
                    cursor.execute(jingcaiSelectSql)
                    result = cursor.fetchall()
                    if result == ():
                        jingCaiInsertSql = 'INSERT INTO jingcai(id, name, createTime, cover) VALUES(%s, %s, %s, %s)'
                        data = (str(id[0]), videoName, str(tenPhoto[0]), videoName)
                        print(data)
                        cursor.execute(jingCaiInsertSql, data)
                        db.commit()
    db.close()
#单个用户生成视频
def userid_toVideo(path,userid):
    print("查找数据库")
    img_array = []
    # 打开数据库连接
    db = pymysql.connect(host="116.63.162.117", user="root", password="123456", database="album")
    # 使用 cursor() 方法创建一个游标对象 cursor
    cursor = db.cursor()
    # 获取该用户生成视频的最新时间
    sql = 'SELECT MAX(createTime) from jingcai where id=' + userid
    cursor.execute(sql)
    MaxCreateTime = cursor.fetchall()
    sql1 = ""
    #如果最新时间不为空，
    if MaxCreateTime[0][0] != None:
        sql1 = 'SELECT  CONVERT(uploadTime,date) as date, count(name) as nameSum from photo WHERE userId = ' + userid + ' GROUP BY date HAVING COUNT(*) >=5 and MAX(date) >="' + str(
            MaxCreateTime[0][0]) + '" ORDER BY date DESC'
    # 如果该用户还没生成视频
    else:
        sql1 = 'SELECT  CONVERT(uploadTime,date) as date, count(name) as nameSum from photo WHERE userId = ' + userid + ' GROUP BY date HAVING COUNT(*) >=5 ORDER BY date DESC'
    print(sql1)
    cursor.execute(sql1)
    # 获取该用户下所有图片大于10张的日期和图片数量
    tenPhotos = cursor.fetchall()
    print(tenPhotos)
    if tenPhotos != ():
        for tenPhoto in tenPhotos:
            sql2 = 'SELECT name from photo WHERE uploadTime LIKE "' + str(
                tenPhoto[0]) + '%"' + ' and userId = ' + userid
            cursor.execute(sql2)
            # 获取该用户下图片最多日期下的图片
            photoNames = cursor.fetchall()
            interval = len(photoNames) // 10 + 1
            print(interval)
            img_array = []
            photoNamelistTemp = list(photoNames)
            photoNamelist = []
            for i in range(len(photoNamelistTemp)):
                if i % interval == 0:
                    photoNamelist.append(photoNamelistTemp[i][0])
            # 遍历该用户、该天上传的所有图片
            print(photoNamelist)
            for i in range(len(photoNamelist)):
                filename = path + "compress_img/" + photoNamelist[i] + '.jpg'
                print(filename)
                img = cv2.imread(filename)
                if img is None:
                    print(filename + " is error!")
                    continue
                img_array.append(img)
            # 图片的大小需要一致
            if img_array != []:
                img_array, size = resize(img_array, 'lagerest')
                fps = 1
                smallvideoUrl = path + 'imgVideo/' + userid + "-" + str(tenPhoto[0]) + "/"
                if os.path.exists(smallvideoUrl) == 0:
                    os.mkdir(smallvideoUrl)
                for i in range(len(img_array)):
                    # 判断小视频是否存在
                    if os.path.exists(smallvideoUrl + photoNamelist[i] + '.avi'):
                        print("该视频已存在")
                        continue
                    # 将封面（第一张图片）保存起来
                    cv2.imwrite(smallvideoUrl + photoNamelist[i] + '.jpg', img_array[i])

                    out = cv2.VideoWriter(smallvideoUrl + photoNamelist[i] + '.avi', cv2.VideoWriter_fourcc(*'DIVX'),
                                          fps, size)
                    out.write(img_array[i])
                    out.release()
                #将封面（第一张图片）保存起来
                cv2.imwrite(path + "cover/" + "origin_" + photoNamelist[0] + '.jpg', img_array[0])
                # 将多个视频拼接,参数有根路径、userId、视频名称
                videoName = userid + "-" + str(tenPhoto[0])
                print(videoName)
                #合成视频
                transitions_animation(path, videoName)
                # 给视频添加背景音乐
                addmusic(path, videoName)
                # 将制作的封面存入cover文件夹
                coverFilename = path + "cover/" + "origin_" + photoNamelist[0] + '.jpg'
                # 生成封面图片
                generateCoverImg(coverFilename, path, videoName + ".jpg", str(tenPhoto[0]))
                # 将生成的视频存入数据库
                jingcaiSelectSql = 'SELECT * from jingcai WHERE id = ' + userid + ' and createTime = "' + str(
                    tenPhoto[0]) + '"'
                print(jingcaiSelectSql)
                cursor.execute(jingcaiSelectSql)
                result = cursor.fetchall()
                if result == ():
                    jingCaiInsertSql = 'INSERT INTO jingcai(id, name, createTime,cover) VALUES(%s, %s, %s, %s)'
                    data = (userid, videoName, str(tenPhoto[0]), videoName)
                    print(data)
                    cursor.execute(jingCaiInsertSql, data)
                    db.commit()

    db.close()


#生成封面图片
def generateCoverImg(coverFilename,path,filename,riqi):
    imageFile = coverFilename
    img = Image.open(imageFile)
    # 在图片上添加文字
    word = f"""     
    精  彩  时  刻

      {riqi}
    """
    width = img.width
    height = img.height
    # 查看图片宽高
    position = (width /8, height /6)
    color = (255, 251, 240)
    draw = ImageDraw.Draw(img)
    # 选择字体与大小
    font = ImageFont.truetype(r'D:/workspace/album_newnew/upload/static/huakang.ttc', 40)
    # font = ImageFont.truetype(r'/home/photoAblum/resource/upload/static/huakang.ttc', 40)
    draw.text(position, word, color, font=font)

    # 保存图片
    img.save(path + 'cover/' + filename)

# 将多个视频拼接
def transitions_animation(path, videoName):
    # 生成目标视频文件
    if os.path.exists(path + "video/" + videoName + "temp" + ".mp4") == 0:
        # 主要是需要moviepy这个库
        # 定义一个数组
        videoTemp = []
        # 访问 video 文件夹 (假设视频都放在这里面)
        for root, dirs, files in os.walk(path + "imgVideo/" + videoName + "/"):
            # 按文件名排序
            files.sort()
            # 遍历所有文件
            for file in files:
                # 如果后缀名为 .mp4
                if os.path.splitext(file)[1] == '.avi':
                    # 拼接成完整路径
                    filePath = os.path.join(root, file)
                    # 载入视频
                    video = VideoFileClip(filePath)

                    videoTemp.append(video)

        # 拼接视频
        final_clip = concatenate_videoclips(videoTemp)
        print(final_clip.size)
        # final_clip = final_clip.add_mask()

        final_clip.write_videofile(path + "video/" + videoName + "temp" + ".mp4", fps=24, codec='libx264', threads=2)


# 给视频加背景音乐(背景音乐时长与视频一致)
def addmusic(path, videoName):
    # 打开视频文件
    video = VideoFileClip(path + "video/" + videoName + "temp" + ".mp4")
    # 打开音频文件
    # audio = AudioFileClip('D:/test2/music.mp3')
    audio = AudioFileClip('/home/photoAblum/resource/upload/static/music.mp3')

    # 获取视频时长
    song = afx.audio_loop(audio, duration=video.duration)

    # 将混合后的音频设置到要输出的视频上
    vclip = video.set_audio(song)
    # 输出视频文件，可以指定视频比率和音频比率，FFmpeg运行速率，线程数量等参数
    vclip.write_videofile(path + "video/" + videoName + ".mp4", fps=24, codec='libx264', threads=2)
    # os.remove(path + "video/" + videoName + "temp" + ".mp4")


if __name__ == "__main__":
    app.config.from_object(Config())
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()
    app.run(host='127.0.0.1', port='5001', debug=True)
    # app.run(host='172.28.241.94', port='5001')
