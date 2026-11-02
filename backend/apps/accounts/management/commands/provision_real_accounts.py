"""生产环境：把默认演示账号换成真实账号，并设置强密码（幂等、可重复执行）。

背景：
  - 部署后站点长期用默认演示账号 admin/admin123（或手写弱密码），属裸奔。
  - 本命令做三件事：
      1) 创建一个「真实超管」(Boss 本人)，role=BOSS，强密码（不传则自动生成并打印一次）；
      2) 停用默认演示 admin 账号（is_active=False 并随机重置其密码），杜绝弱口令登录；
      3) 可选：按 REAL_EMPLOYEES_JSON 批量创建正式员工账号（带强密码）。

用法（在 web 容器内执行）：
  docker compose -f deploy/prod/docker-compose.yml --env-file deploy/prod/.env exec web \
    python manage.py provision_real_accounts

环境变量（均可选，不填走安全默认值）：
  REAL_ADMIN_USER    真实超管登录名（默认 luosifu）
  REAL_ADMIN_NAME    真实姓名（默认 罗斯福，拆成 first/last name）
  REAL_ADMIN_EMAIL   邮箱（默认 boss@yuncaishuitong.com）
  REAL_ADMIN_PASS    指定密码（留空=自动生成 24 位强密码并打印）
  DISABLE_DEMO_ADMIN 是否停用演示 admin（默认 true）
  REAL_EMPLOYEES_JSON  员工列表 JSON，例：
    [{"username":"xiaozhang","name":"小张","role":"EMPLOYEE","dept":"SALES","phone":"13800000000"},
     {"username":"xiaoli","name":"小李","role":"HR","dept":"MGMT","phone":"13900000000"}]
"""
import os
import json
import secrets
import string

from django.core.management.base import BaseCommand
from apps.accounts.models import User, Department


def gen_strong_password(length=24):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = "生产环境：创建真实超管 + 停用演示 admin + 可选批量建员工（强密码）"

    def handle(self, *args, **options):
        # ---------- 1) 真实超管 ----------
        un = os.environ.get("REAL_ADMIN_USER", "luosifu").strip()
        full_name = os.environ.get("REAL_ADMIN_NAME", "罗斯福").strip()
        email = os.environ.get("REAL_ADMIN_EMAIL", "boss@yuncaishuitong.com").strip()
        pw = os.environ.get("REAL_ADMIN_PASS", "").strip()

        first = full_name[0] if full_name else un
        last = full_name[1:] if len(full_name) > 1 else ""

        user, created = User.objects.get_or_create(
            username=un,
            defaults={
                "email": email,
                "first_name": first,
                "last_name": last,
                "role": "BOSS",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if not created:
            user.role = "BOSS"
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.email = email
            user.first_name = first
            user.last_name = last

        if not pw:
            pw = gen_strong_password(24)
        user.set_password(pw)
        user.save()
        self.stdout.write(self.style.SUCCESS(
            f"真实超管就绪 → 登录名: {un}  密码: {pw}  （请立即抄到密码管理器，不会再次显示）"
        ))

        # ---------- 2) 停用演示 admin ----------
        if os.environ.get("DISABLE_DEMO_ADMIN", "true").lower() in ("1", "true", "yes", "y"):
            for demo in User.objects.filter(username="admin"):
                demo.is_active = False
                demo.set_password(gen_strong_password(32))  # 废掉弱口令
                demo.save()
                self.stdout.write(self.style.WARNING(
                    f"已停用演示 admin 账号({demo.username})并重置其密码，无法再用 admin/admin123 登录"
                ))

        # ---------- 3) 可选批量建员工 ----------
        raw = os.environ.get("REAL_EMPLOYEES_JSON", "").strip()
        if raw:
            try:
                employees = json.loads(raw)
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f"REAL_EMPLOYEES_JSON 解析失败: {e}"))
                employees = []
            dept_cache = {d.code: d for d in Department.objects.all()}
            for emp in employees:
                eu = emp.get("username")
                if not eu:
                    continue
                epw = gen_strong_password(20)
                e_first = emp.get("name", eu)[:1]
                e_last = emp.get("name", eu)[1:]
                eu_obj, ec = User.objects.get_or_create(
                    username=eu,
                    defaults={
                        "email": emp.get("email", f"{eu}@yuncaishuitong.com"),
                        "first_name": e_first,
                        "last_name": e_last,
                        "role": emp.get("role", "EMPLOYEE"),
                        "department": dept_cache.get(emp.get("dept")) if emp.get("dept") else None,
                        "phone": emp.get("phone", ""),
                        "is_staff": emp.get("role") in ("BOSS", "HR", "MANAGER", "LEADER"),
                        "is_superuser": emp.get("role") == "BOSS",
                        "is_active": True,
                    },
                )
                if ec:
                    eu_obj.set_password(epw)
                    eu_obj.save()
                    self.stdout.write(self.style.SUCCESS(
                        f"员工账号已建 → {eu}（{emp.get('name','')}） 密码: {epw}"
                    ))
                else:
                    self.stdout.write(self.style.WARNING(f"员工 {eu} 已存在，跳过（不覆盖密码）"))

        self.stdout.write(self.style.SUCCESS("✅ 账号处置完成。请到 https://yuncaishuitong.com/admin/ 复核。"))
