from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import os
import numpy as np
from PIL import Image
import cv2
from ultralytics import YOLO
import torch
import random
from werkzeug.utils import secure_filename
import base64
from io import BytesIO
import datetime
from flask_sqlalchemy import SQLAlchemy
import openpyxl
# 初始化 Flask 应用
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用于会话管理
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# 创建上传文件夹（如果不存在）
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 配置 MySQL 数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/high_grass'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db = SQLAlchemy(app)

# 定义数据库模型
class User(db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(20), unique=True, nullable=False)
    user_password = db.Column(db.String(20), nullable=False)
    user_email = db.Column(db.String(20), unique=True, nullable=False)

    def __repr__(self):
        return f"User('{self.user_name}', '{self.user_email}')"

class Plant(db.Model):
    __tablename__ = 'plantinfo'
    PlantID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100), nullable=False)
    Family = db.Column(db.String(100), nullable=False)
    Genus = db.Column(db.String(100), nullable=False)
    Species = db.Column(db.String(100), nullable=False)
    Distribution = db.Column(db.String(255), nullable=False)
    Appearance = db.Column(db.Text, nullable=True)
    MedicinalValue = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"Plant('{self.Name}', '{self.Family}')"

class PlantRecognition(db.Model):
    __tablename__ = 'recognitions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    image_path = db.Column(db.String(200), nullable=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plantinfo.PlantID'), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"Recognition('{self.user_id}', '{self.plant_id}', '{self.confidence}')"


# 加载 YOLO 模型
model_path = "best.pt"  # 确保你的模型文件在此目录下
if not os.path.exists(model_path):
    raise FileNotFoundError(f"模型文件 {model_path} 不存在")
model = YOLO(model_path)
class_names = model.names

# 加载植物详细信息
excel_path = "plant.xlsx"  # 确保你的 Excel 文件在此目录下
plant_info = {}

def load_plant_info():
    global plant_info
    if os.path.exists(excel_path):
        try:
            wb = openpyxl.load_workbook(excel_path)
            sheet = wb.active
            for row in sheet.iter_rows(min_row=2, values_only=True):  # 跳过表头
                if row[0]:  # 确保种名存在
                    plant_name = row[0]
                    plant_info[plant_name] = {
                        "科": row[1],
                        "属": row[2],
                        "种": row[0],
                        "分布地点": row[4],
                        "外观": row[5]
                    }
            print(f"成功加载 {len(plant_info)} 种植物信息")
        except Exception as e:
            print(f"加载植物信息失败: {e}")
    else:
        print(f"Excel 文件不存在: {excel_path}")


load_plant_info()

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def classify_image(image_path):
    try:
        results = model.predict(image_path)
        if results:
            probs = results[0].probs
            if isinstance(probs, torch.Tensor):
                class_id = torch.argmax(probs).item()
                confidence = probs[class_id].item()
            else:
                class_id = torch.argmax(probs.data).item()
                confidence = probs.data[class_id].item()

            class_name = class_names[class_id]

            # 减去一个随机数（范围在1%到5%之间，保留两位小数）
            random_num = round(random.uniform(0.01, 0.05), 4)
            adjusted_confidence = max(confidence - random_num, 0)

            # 获取详细信息
            plant_data = plant_info.get(class_name, {})

            return {
                "class_name": class_name,
                "confidence": adjusted_confidence,
                "details": plant_data
            }
        else:
            return None
    except Exception as e:
        print(f"分类图像失败: {e}")
        return None
def process_image(image_data):
    try:
        # 将 base64 图像数据转换为图像
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp.jpg')
        image.save(image_path)

        # 分类图像
        return classify_image(image_path)
    except Exception as e:
        print(f"处理图像失败: {e}")
        return None

# 路由 - 登录页面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 使用前端表单字段名称
        username = request.form.get('username')  # 修改为前端实际使用的字段名称
        password = request.form.get('password')  # 修改为前端实际使用的字段名称

        if not username or not password:
            flash('用户名和密码不能为空')
            return render_template('login.html')

        user = User.query.filter_by(user_name=username, user_password=password).first()
        if user:
            session['isAuthenticated'] = True
            session['user_id'] = user.user_id
            session['user_name'] = user.user_name
            print(f'登录成功: {username}')
            return redirect(url_for('index'))
        else:
            print('用户名或密码错误')
            flash('用户名或密码错误')

    return render_template('login.html')

# 路由 - 注册页面
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if not username or not email or not password or not confirm_password:
            flash('所有字段均不能为空')
            return render_template('register.html')
        if password != confirm_password:
            flash('两次输入的密码不一致')
            return render_template('register.html')
        existing_user = User.query.filter_by(user_name=username).first()
        if existing_user:
            flash('用户名已存在')
            return render_template('register.html')
        new_user = User(user_name=username, user_email=email, user_password=password)
        db.session.add(new_user)
        db.session.commit()
        session['isAuthenticated'] = True
        session['user_name'] = username
        flash('注册成功')
        return redirect(url_for('login'))
    return render_template('register.html')

# 路由 - 登出
@app.route('/logout')
def logout():
    session.pop('isAuthenticated', None)
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('isAuthenticated'):
        return redirect(url_for('login'))
    # 使用 session['user_name'] 而不是不存在的 session['username']
    return render_template('index.html', username=session['user_name'])

@app.route('/plant-identification')
def plant_identification():
    return render_template('plant-identification.html')

@app.route('/info-query')
def info_query():
    return render_template('plant-info.html')

@app.route('/smart-recommendation')
def smart_recommendation():
    return render_template('recommendations.html')

@app.route('/Personal-Information')
def Personal_Information():
    return render_template('OUR.html')


# # 路由 - 植物识别 API
@app.route('/api/plant-identification1', methods=['POST'])
def plant_identification1():
    if 'file' not in request.files:
        return jsonify({"error": "未上传文件"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "未选择文件"}), 400

    if file and allowed_file(file.filename):
        # 保存上传的文件
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        # 分类图像
        result = classify_image(file_path)
        if result:
            return jsonify({
                "status": "success",
                "class_name": result["class_name"],
                "confidence": result["confidence"],
                "details": result["details"]
            })
        else:
            return jsonify({"status": "error", "message": "无法识别植物"}), 400
    else:
        return jsonify({"error": "不支持的文件格式"}), 400


# 路由 - 获取热门植物
@app.route('/api/popular-plants', methods=['GET'])
def popular_plants():
    # 这里应该从数据库获取热门植物数据
    # 模拟返回一些植物数据
    mock_plants = [
        {"id": 1, "name": "暗紫贝母", "family": "景天科", "genus": "红景天属",
         "image": "static/0_百日菊.jpg"},
        {"id": 2, "name": "百日菊", "family": "菊科", "genus": "风毛菊属",
         "image": "static/1_百日菊.jpg"},
        {"id": 3, "name": "大丽花", "family": "麻黄科", "genus": "麻黄属",
         "image": "static/2_百日菊.jpg"},
        {"id": 4, "name": "星舌紫菀", "family": "杜鹃花科", "genus": "杜鹃属",
         "image": "static/3_百日菊.jpg"}
    ]
    return jsonify(mock_plants)


@app.route('/api/plant-info', methods=['GET'])
def plant_info_search():
    query = request.args.get('query', '')
    search_type = request.args.get('type', 'name').lower()  # 默认按名称查询

    if not query:
        return jsonify([])

    try:
        query_lower = query.lower()
        results = []

        # 查询数据库中的植物信息
        if search_type == 'name':
            plants = Plant.query.filter(Plant.Name.ilike(f'%{query_lower}%')).all()
        elif search_type == 'family':
            plants = Plant.query.filter(Plant.Family.ilike(f'%{query_lower}%')).all()
        elif search_type == 'location':
            plants = Plant.query.filter(Plant.Distribution.ilike(f'%{query_lower}%')).all()
        else:
            # 如果没有匹配的搜索类型，默认返回空列表
            return jsonify([])

        if plants:
            for plant in plants:
                plant_data = {
                    "id": plant.PlantID,
                    "name": plant.Name,
                    "family": plant.Family,
                    "genus": plant.Genus,
                    "location": plant.Distribution,
                    "appearance": plant.Appearance,
                    # 使用稳定的图片链接替代动态链接
                    "image": f"static/{plant.Name}.jpg"
                }
                results.append(plant_data)

        return jsonify(results)

    except Exception as e:
        print(f"信息查询失败: {e}")
        return jsonify({"status": "error", "message": "信息查询失败"}), 500


# 路由 - 智能推荐 API
@app.route('/api/recommendations', methods=['GET'])
def plant_recommendations():
    try:
        # 模拟推荐算法，实际应用中可以根据用户历史和植物特征进行智能推荐
        all_plants = [
            {"id": 1, "name": "红景天", "family": "景天科", "genus": "红景天属",
             "location": "高山地区", "appearance": "多年生草本植物",
             "image": "https://picsum.photos/seed/plant1/600/400"},
            {"id": 2, "name": "雪莲花", "family": "菊科", "genus": "风毛菊属",
             "location": "高海拔地区", "appearance": "白色花瓣",
             "image": "https://picsum.photos/seed/plant2/600/400"},
            {"id": 3, "name": "藏麻黄", "family": "麻黄科", "genus": "麻黄属",
             "location": "干旱地区", "appearance": "针叶状",
             "image": "https://picsum.photos/seed/plant3/600/400"},
            {"id": 4, "name": "高原杜鹃", "family": "杜鹃花科", "genus": "杜鹃属",
             "location": "高山地带", "appearance": "灌木",
             "image": "https://picsum.photos/seed/plant4/600/400"},
            {"id": 5, "name": "藏红花", "family": "鸢尾科", "genus": "番红花属",
             "location": "高原地区", "appearance": "橙红色花瓣",
             "image": "https://picsum.photos/seed/plant5/600/400"},
            {"id": 6, "name": "高山草", "family": "禾本科", "genus": "高山草属",
             "location": "高山草地", "appearance": "多年生草本",
             "image": "https://picsum.photos/seed/plant6/600/400"},
            {"id": 7, "name": "藏药草", "family": "唇形科", "genus": "藏药草属",
             "location": "藏区", "appearance": "小叶",
             "image": "https://picsum.photos/seed/plant7/600/400"},
            {"id": 8, "name": "高原菊", "family": "菊科", "genus": "高原菊属",
             "location": "高原地带", "appearance": "黄色花瓣",
             "image": "https://picsum.photos/seed/plant8/600/400"},
            {"id": 9, "name": "藏玫瑰", "family": "蔷薇科", "genus": "藏玫瑰属",
             "location": "高原地带", "appearance": "红色花瓣",
             "image": "https://picsum.photos/seed/plant9/600/400"},
            {"id": 10, "name": "高原松", "family": "松科", "genus": "松属",
             "location": "高山地区", "appearance": "针叶常绿",
             "image": "https://picsum.photos/seed/plant10/600/400"},
            {"id": 11, "name": "藏药花", "family": "菊科", "genus": "藏药花属",
             "location": "藏区", "appearance": "黄色花瓣",
             "image": "https://picsum.photos/seed/plant11/600/400"},
            {"id": 12, "name": "高原草", "family": "禾本科", "genus": "高原草属",
             "location": "高原地带", "appearance": "多年生草本",
             "image": "https://picsum.photos/seed/plant12/600/400"}
        ]

        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 8))
        start = (page - 1) * limit
        end = start + limit

        # 随机打乱结果以模拟推荐算法
        random.shuffle(all_plants)

        # 返回当前页的数据
        current_page_plants = all_plants[start:end]

        return jsonify(current_page_plants)
    except Exception as e:
        print(f"智能推荐失败: {e}")
        return jsonify({"status": "error", "message": "智能推荐失败"}), 500


if __name__ == '__main__':
    app.run(debug=True)