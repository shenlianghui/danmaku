# B站弹幕分析系统

这是一个基于Python(Django)和Vue.js的B站视频弹幕分析系统，可以爬取、存储、分析和可视化B站视频弹幕数据。

## 功能特点

- **弹幕爬取**：自动爬取指定B站视频的弹幕数据
- **数据存储**：将爬取的弹幕数据存储到数据库中
- **数据分析**：对弹幕数据进行多维度分析
  - 关键词提取
  - 情感分析
  - 时间线分析
  - 用户活跃度分析
- **可视化展示**：通过图表和词云等形式直观呈现分析结果

## 系统架构

- **后端**：Django + Django REST Framework
- **前端**：Vue.js + Element Plus
- **数据库**：SQLite (开发) / MySQL (生产)
- **分析工具**：Pandas, NumPy, Jieba, Scikit-learn

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 14+
- npm 6+

### 后端安装

1. 克隆项目
```bash
git clone https://github.com/yourusername/danmaku-analyzer.git
cd danmaku-analyzer
```

2. 创建虚拟环境
```bash
python -m venv venv
```

3. 激活虚拟环境
```bash
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

4. 安装依赖
```bash
pip install -r requirements.txt
```

5. 数据库迁移
```bash
python manage.py migrate
```

6. 创建管理员用户
```bash
python manage.py createsuperuser
```

7. 启动开发服务器
```bash
python manage.py runserver
```

### 前端安装

1. 进入前端目录
```bash
cd frontend
```

2. 安装依赖
```bash
npm install
```

3. 启动开发服务器
```bash
npm run serve
```

## 使用指南

1. 访问系统首页：http://localhost:8080
2. 输入B站视频URL或BV号，开始爬取弹幕
3. 在弹幕爬取页面查看爬取任务状态
4. 对已爬取的视频进行弹幕分析
5. 查看分析结果可视化

## API接口

系统提供了RESTful API接口，可以通过以下URL访问：

- API根路径：http://localhost:8000/api/
- 可浏览的API文档：http://localhost:8000/api-auth/

主要接口包括：

- `/api/videos/` - 视频信息管理
- `/api/danmakus/` - 弹幕数据查询
- `/api/tasks/` - 爬取任务管理
- `/api/analyses/` - 分析结果管理

## 项目结构

```
danmaku/
├── danmaku_system/        # 项目配置
├── danmaku_crawler/       # 弹幕爬虫应用
├── danmaku_analysis/      # 弹幕分析应用
├── frontend/              # Vue.js前端
├── venv/                  # 虚拟环境
└── manage.py              # Django管理脚本
```

## 贡献指南

欢迎贡献代码或提出建议，请遵循以下步骤：

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

本项目采用MIT许可证，详情请参阅LICENSE文件。

## 鸣谢

- [Bilibili](https://www.bilibili.com/) - 数据来源
- [Django](https://www.djangoproject.com/) - 后端框架
- [Vue.js](https://vuejs.org/) - 前端框架
- [Element Plus](https://element-plus.org/) - UI组件库 