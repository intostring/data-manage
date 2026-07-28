# 数据管理平台

对数据表进行展示和增删改查的平台。支持管理阿里云 MySQL 上已有数据表，也支持 CSV 上传动态建表。

## 技术栈

- **后端**：Django 4.2 + Django REST Framework + PyMySQL
- **前端**：Vue 3 + Vite + Tailwind CSS（自研 UI 组件）
- **数据库**：MySQL（阿里云 RDS）

## 目录结构

```
ylweb/
├── backend/          Django 后端
│   ├── config/       项目设置
│   ├── apps/
│   │   ├── data_tables/      已有 MySQL 表管理（inspectdb 生成）
│   │   ├── dynamic_tables/   CSV 动态上传建表
│   │   └── accounts/         登录认证
│   └── utils/        分页等工具
└── frontend/         Vue 3 前端
    └── src/
        ├── components/ui/    自研 Base 组件
        ├── views/            Login/Dashboard/TableView/UploadTable
        └── stores/           Pinia 状态管理
```

## 启动方式

### 1. 后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置数据库连接
cp .env.example .env
# 编辑 .env 填入阿里云 MySQL 连接信息

# 接入已有 MySQL 表（反向生成模型）
python manage.py inspectdb > apps/data_tables/models.py
# 编辑生成的 models.py，保留需要管理的表
# 在 apps/data_tables/registry.py 中按需注册表

# 执行迁移（创建动态表元信息表 + Token 表）
python manage.py migrate

# 创建管理员账号
python manage.py createsuperuser

# 启动
python manage.py runserver
```

后端运行在 http://localhost:8000

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

前端运行在 http://localhost:5173 ，已配置代理转发 `/api` 到后端。

### 3. 使用

1. 浏览器打开 http://localhost:5173
2. 用 createsuperuser 创建的账号登录
3. 左侧导航选择已有表查看/编辑数据
4. 点击「上传数据」上传 CSV 创建新表

## 接入已有表

在 `backend/apps/data_tables/` 下：

1. 运行 `python manage.py inspectdb > apps/data_tables/models.py`
2. 检查生成的模型，保留 `managed = False`（已有表不由 Django 管理迁移）
3. 在 `serializers.py` 为每张表编写 Serializer
4. 在 `serializers.py` 末尾用 `table_registry.register('url标识', Model, Serializer)` 注册

注册后该表自动获得完整 CRUD 接口：`/api/tables/<url标识>/`

## 设计说明

UI 采用极简专业风（Linear/Notion 质感）：

- 白底 + 焦糖橙（#C2410C）强调色
- 无紫蓝渐变、无 emoji、无毛玻璃
- 自研组件（BaseTable/BaseModal/BaseButton 等），不依赖成品 UI 库
- 强调色统一在 `frontend/tailwind.config.js` 一处可调
