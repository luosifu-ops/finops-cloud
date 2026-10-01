# 生产 gunicorn 配置（bare-metal 直接启动时用：gunicorn -c deploy/prod/gunicorn.conf.py config.wsgi:application）
bind = "0.0.0.0:8000"
workers = 3
timeout = 120
accesslog = "-"
errorlog = "-"
