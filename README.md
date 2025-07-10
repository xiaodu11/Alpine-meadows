# 高原百草库
**采用Flask框架与yolo11对图片进行识别<br>**
best.pt:yolo11训练的最优模型（100epoch）<br>
high_grass.sql:数据库，导入修改即可<br>
yolo_web:运行文件<br>

## 运行注意：
**安装深度学习环境：python>=3.6 conda>=2.2**<br>
**根据python文件安装相关库**<br>
自己电脑运行代码：直接运行即可<br>
服务器运行代码：gunicorn -w 2 -b 0.0.0.0:80 yolo_web:app<br>

