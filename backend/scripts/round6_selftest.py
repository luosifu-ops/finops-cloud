"""第六轮增量自测：菜单归类 / 线索编辑删除 / 团队汇总

用法：venv/bin/python scripts/round6_selftest.py
覆盖：
  1. 菜单：员工管理 / 部门与小组 归入行政人事部；外勤部 / 增值业务部 独立为一级分组
  2. 运营部线索池：编辑（Lead + LeadExt 双写、留操作日志）、删除（软删 + 出公海）、越权 403
  3. 团队汇总：提交日报自动生成、主管编辑保留、重复提交不覆盖、重新生成强制覆盖、员工看不到
测试数据全部清理。
"""
import os
import sys

import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.hashers import make_password  # noqa: E402
from django.utils import timezone  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from apps.accounts.models import Department, Team, User  # noqa: E402
from apps.common.models import OperationLog  # noqa: E402
from apps.growth.models import LeadChannel, LeadExt, LeadPool  # noqa: E402
from apps.reports.models import DailyReport, TeamSummary  # noqa: E402
from apps.sales.models import Lead  # noqa: E402
from apps.reports import aggregation  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, extra=""):
    (PASS if ok else FAIL).append(name)
    print(("  [OK]   " if ok else "  [FAIL] ") + name + (("  -> " + str(extra)) if extra else ""))


def router_text():
    p = os.path.abspath(os.path.join(BASE_DIR, "..", "web", "src", "router", "index.js"))
    with open(p, encoding="utf-8") as f:
        return f.read()


print("\n== 1. 菜单归类 ==")
txt = router_text()
emp_line = [ln for ln in txt.splitlines() if "title: '员工管理'" in ln]
dept_line = [ln for ln in txt.splitlines() if "title: '部门与小组'" in ln]
check("员工管理唯一一条", len(emp_line) == 1, len(emp_line))
if emp_line:
    check("员工管理归入行政人事部", "group: '行政人事部'" in emp_line[0])
    check("员工管理已不在系统管理", "group: '系统管理'" not in emp_line[0])
if dept_line:
    check("部门与小组归入行政人事部", "group: '行政人事部'" in dept_line[0])
    check("部门与小组已不在系统管理", "group: '系统管理'" not in dept_line[0])

field_line = [ln for ln in txt.splitlines() if "growth-field-tasks" in ln and "path:" in ln]
value_line = [ln for ln in txt.splitlines() if "growth-value-added" in ln and "path:" in ln]
check("外勤任务池独立为「外勤部」", bool(field_line) and "group: '外勤部'" in field_line[0],
      field_line[0].strip()[:90] if field_line else "")
check("外勤任务池已脱离增长中心", bool(field_line) and "group: '增长中心'" not in field_line[0])
check("外勤任务池不再挂在二级菜单", bool(field_line) and "parent:" not in field_line[0])
check("增值业务独立为「增值业务部」", bool(value_line) and "group: '增值业务部'" in value_line[0],
      value_line[0].strip()[:90] if value_line else "")
check("增值业务已脱离增长中心", bool(value_line) and "group: '增长中心'" not in value_line[0])
check("增值业务不再挂在二级菜单", bool(value_line) and "parent:" not in value_line[0])

growth_lines = [ln for ln in txt.splitlines() if "group: '增长中心'" in ln]
check("增长中心分组内已无外勤 / 增值业务",
      not any("growth-field-tasks" in ln or "growth-value-added" in ln for ln in growth_lines),
      len(growth_lines))

# ------------------------------------------------------------------ 2. 线索编辑/删除
print("\n== 2. 运营部线索池：编辑 / 删除 ==")
boss = User.objects.filter(is_active=True, role="BOSS").first() or \
    User.objects.filter(is_active=True, is_superuser=True).first()
ops_user = None
from apps.growth.models import GrowthRole  # noqa: E402
for r in GrowthRole.objects.filter(role="OPS").select_related("user"):
    if r.user and r.user.is_active:
        ops_user = r.user
        break
if ops_user is None:
    ops_user = User.objects.filter(is_active=True).exclude(id=boss.id).first()
other = User.objects.filter(is_active=True, role="EMPLOYEE", is_superuser=False) \
    .exclude(id__in=[boss.id, ops_user.id]).first()
channel = LeadChannel.objects.filter(is_deleted=False).first()
print(f"  账号：BOSS={boss.username} 归属运营={ops_user.username} 其他员工={other.username if other else '-'}")

lead = Lead.objects.create(name="自测-线索编辑前", phone="19900000101", created_by=ops_user)
ext = LeadExt.objects.create(lead=lead, channel=channel, in_pool=True, created_by=ops_user,
                             ops_owner=ops_user, source_account_no="SELFTEST-OLD",
                             contact_type="PHONE", contact_value="19900000101")
LeadPool.objects.create(lead_ext=ext, status="WAITING", created_by=ops_user)

c = APIClient()
c.force_authenticate(user=ops_user)
r = c.patch(f"/api/growth/leads/{ext.id}/", {
    "name": "自测-线索编辑后", "phone": "19900000102", "contact_value": "19900000102",
    "source_account_no": "SELFTEST-NEW", "customer_need": "需要代理记账+注册",
}, format="json")
check("归属运营本人可编辑（200）", r.status_code == 200, r.status_code)
lead.refresh_from_db()
ext.refresh_from_db()
check("原线索姓名已更新", lead.name == "自测-线索编辑后", lead.name)
check("原线索电话已更新", lead.phone == "19900000102", lead.phone)
check("来源账号已更新", ext.source_account_no == "SELFTEST-NEW", ext.source_account_no)
check("联系方式已更新", ext.contact_value == "19900000102", ext.contact_value)
check("客户需求已更新", "代理记账" in (ext.customer_need or ""), ext.customer_need)
check("已写入修改操作日志",
      OperationLog.objects.filter(module="运营线索池", action="UPDATE",
                                  object_id=str(ext.id)).exists())

if other:
    c2 = APIClient()
    c2.force_authenticate(user=other)
    r2 = c2.patch(f"/api/growth/leads/{ext.id}/", {"name": "越权改名"}, format="json")
    check("非归属员工不可编辑（403）", r2.status_code == 403, r2.status_code)
    r3 = c2.delete(f"/api/growth/leads/{ext.id}/")
    check("非归属员工不可删除（403）", r3.status_code == 403, r3.status_code)

# 姓名不允许改空
r4 = c.patch(f"/api/growth/leads/{ext.id}/", {"name": "   "}, format="json")
check("客户姓名不能改为空（400）", r4.status_code == 400, r4.status_code)

r5 = c.delete(f"/api/growth/leads/{ext.id}/")
check("归属运营本人可删除（204）", r5.status_code == 204, r5.status_code)
ext.refresh_from_db()
check("线索已软删除", ext.is_deleted is True, ext.is_deleted)
check("删除后已移出公海", ext.in_pool is False, ext.in_pool)
pool = LeadPool.objects.filter(lead_ext_id=ext.id).first()
check("公海记录同步作废", pool is None or pool.is_deleted is True,
      None if pool is None else pool.is_deleted)
r6 = c.get("/api/growth/leads/", {"page_size": 200})
rows = r6.json().get("results", r6.json()) if r6.status_code == 200 else []
check("删除后列表不再返回该线索",
      all(x.get("id") != ext.id for x in rows), len(rows))
check("已写入删除操作日志",
      OperationLog.objects.filter(module="运营线索池", action="DELETE",
                                  object_id=str(ext.id)).exists())

# ------------------------------------------------------------------ 3. 团队汇总
print("\n== 3. 工作汇报：团队汇总 ==")
dept = Department.objects.filter(name="销售部").first() or Department.objects.first()
team = Team.objects.filter(department=dept).first()
tmp_user = User.objects.create(
    username="selftest6_tmp", first_name="自测", last_name="六",
    department=dept, team=team, role="EMPLOYEE", status="REGULAR",
    password=make_password("SelfTest6!2026"),
)
today = timezone.localdate()
period = str(today)
print(f"  临时员工：{tmp_user.username} 部门={dept.name} 小组={team.name if team else '-'}")

cu = APIClient()
cu.force_authenticate(user=tmp_user)
r = cu.post("/api/reports/daily-reports/save-or-update/", {
    "date": period, "status": "SUBMITTED",
    "today_done": "自测：完成 3 家客户回访", "tomorrow_plan": "自测：跟进签约",
    "today_data": {"calls": 20, "wechat": 5},
}, format="json")
check("日报提交成功", r.status_code == 200, r.status_code)

before = TeamSummary.objects.filter(kind="DAILY", period=period, department=dept,
                                    team=team).count()
summary = TeamSummary.objects.filter(kind="DAILY", period=period, department=dept,
                                     team=team).first()
check("提交后自动生成团队汇总", summary is not None, before)
if summary:
    check("汇总正文含该员工内容",
          "自测：完成 3 家客户回访" in (summary.content or ""), summary.content[:60])
    check("汇总统计已累加", summary.stats.get("calls") in (20, 20.0), summary.stats)
    check("已提交人数已统计", summary.submitted_total >= 1, summary.submitted_total)
    check("在职人数已统计", summary.member_total >= 1, summary.member_total)
    check("来源汇报ID已记录", tmp_user.id and len(summary.source_ids) >= 1, summary.source_ids)
    sid = summary.id

    # 主管编辑（BOSS 视同管理层）
    cb = APIClient()
    cb.force_authenticate(user=boss)
    lst = cb.get("/api/reports/team-summaries/", {"kind": "DAILY", "period": period})
    check("老板可查看团队汇总列表", lst.status_code == 200 and lst.json().get("count", 0) >= 1,
          lst.status_code)
    r = cb.patch(f"/api/reports/team-summaries/{sid}/",
                 {"content": "自测：主管补充的汇总结论"}, format="json")
    check("主管可编辑汇总内容（200）", r.status_code == 200, r.status_code)
    summary.refresh_from_db()
    check("编辑内容已保存", summary.content == "自测：主管补充的汇总结论", summary.content[:40])
    check("已标记人工编辑", summary.is_edited is True, summary.is_edited)
    check("已记录编辑人", summary.edited_by_id == boss.id, summary.edited_by_id)

    # 再次提交同周期日报：不得覆盖人工内容
    cu.post("/api/reports/daily-reports/save-or-update/", {
        "date": period, "status": "SUBMITTED",
        "today_done": "自测：第二次提交", "today_data": {"calls": 30},
    }, format="json")
    summary.refresh_from_db()
    check("重复提交不覆盖人工编辑内容",
          summary.content == "自测：主管补充的汇总结论", summary.content[:40])
    check("重复提交仍刷新统计", summary.stats.get("calls") in (30, 30.0), summary.stats)

    # 重新生成：强制按最新汇报重建
    r = cb.post(f"/api/reports/team-summaries/{sid}/rebuild/")
    check("重新生成成功（200）", r.status_code == 200, r.status_code)
    summary.refresh_from_db()
    check("重新生成后正文回到自动汇总",
          "自测：第二次提交" in (summary.content or ""), summary.content[:60])
    check("重新生成后解除人工编辑标记", summary.is_edited is False, summary.is_edited)

# 员工看不到团队汇总
if other:
    co = APIClient()
    co.force_authenticate(user=other)
    ro = co.get("/api/reports/team-summaries/")
    cnt = ro.json().get("count", 0) if ro.status_code == 200 else -1
    check("普通员工看不到团队汇总（0 条）", ro.status_code == 200 and cnt == 0, cnt)

# ------------------------------------------------------------------ 清理
print("\n== 清理自测数据 ==")
DailyReport.objects.filter(user=tmp_user).delete()
tmp_user.delete()
LeadPool.objects.filter(lead_ext__lead__name__startswith="自测-").delete()
LeadExt.objects.filter(lead__name__startswith="自测-").delete()
Lead.objects.filter(name__startswith="自测-").delete()
# 汇总按真实数据重建一次，去掉自测员工痕迹
for kind, per in [(("DAILY"), period)]:
    aggregation.rebuild(kind, per, dept, team, force=True)
print("  已清理临时员工 / 线索 / 日报，并重建受影响汇总")

print("\n================ 汇总 ================")
print(f"通过 {len(PASS)} 项，失败 {len(FAIL)} 项")
if FAIL:
    for f in FAIL:
        print("  失败：", f)
    sys.exit(1)
