# 部署说明

推荐生产结构：

- 前端：`frontend/dist` 由 nginx 静态托管
- 后端：Django 由 gunicorn 监听 `127.0.0.1:8000`
- nginx：反向代理 `/api/` 与 `/admin/`

服务器目录示例：

```bash
/var/www/data-manage
├── backend
└── frontend
```

部署步骤：

```bash
cd /var/www/data-manage
git pull origin main

cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput

cd ../frontend
npm ci
npm run build
```

服务配置：

```bash
sudo cp deploy/data-manage.service.example /etc/systemd/system/data-manage.service
sudo cp deploy/nginx-data-manage.conf.example /etc/nginx/conf.d/data-manage.conf
sudo systemctl daemon-reload
sudo systemctl enable --now data-manage
sudo nginx -t
sudo systemctl reload nginx
```
