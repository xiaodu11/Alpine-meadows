# 高原百草库
**采用Flask框架与yolo11对图片进行识别<br>**
best.pt:yolo11训练的最优模型（100epoch）<br>
high_grass.sql:数据库，导入修改即可<br>
yolo_web:运行文件<br>
数据均为：网络爬取<br>
要获取更多数据，推荐:
https://ppbc.iplant.cn/ 获取资源<br>

## 运行注意
**安装深度学习环境：python>=3.6 conda>=2.2**<br>
**根据python文件安装相关库**<br>
自己电脑运行代码：直接运行即可<br>
服务器运行代码：<br>
<pre>
gunicorn -w 2 -b 0.0.0.0:80 yolo_web:app
</pre><br>

**yolo_ui.py**为PyQT5库所写代码，运行生成一个页面<br>
**推荐使用pyinstall或者其他打包软件进行打包**

## 效果
**登录界面：**
![image](https://github.com/user-attachments/assets/94b8b638-21d6-4c47-8d6e-032ee32c9992)<br>
<br>
<br>
**主页：**
![image](https://github.com/user-attachments/assets/f77797b9-42ec-4209-bb4a-bc084e164dea)<br>



