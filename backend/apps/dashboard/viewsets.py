"""老板驾驶舱 / 全员数据看板聚合接口"""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User, Department
from apps.sales.models import Contract, Lead, SalesTarget, CallRecord
from apps.accounting.models import MonthlyTask, AccountingClient
from apps.ops.models import AdDailyStat, AdPlatform
from apps.hr.models import Attendance, LeaveApplication
from apps.reports.models import DailyReport


def _month_str(d=None):
    return (d or timezone.now().date()).strftime("%Y-%m")


def _month_range(month):
    y, m = int(month[:4]), int(month[5:7])
    start = date(y, m, 1)
    if m == 12:
        end = date(y + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(y, m + 1, 1) - timedelta(days=1)
    return start, end


def _scope_users(request):
    """按角色返回可见用户 queryset"""
    u = request.user
    if u.is_superuser or u.role in ("BOSS", "HR"):
        return User.objects.filter(is_active=True)
    if u.role == "MANAGER" and u.department_id:
        return User.objects.filter(department_id=u.department_id, is_active=True)
    if u.role == "LEADER" and u.team_id:
        return User.objects.filter(team_id=u.team_id, is_active=True)
    return User.objects.filter(id=u.id)


@api_view(["GET"])
def overview(request):
    """老板总览：一屏看全公司"""
    month = request.query_params.get("month") or _month_str()
    start, end = _month_range(month)
    today = timezone.now().date()

    contracts = Contract.objects.filter(signed_date__gte=start, signed_date__lte=end)
    perf = contracts.aggregate(total=Sum("amount"), received=Sum("received"), cnt=Count("id"))
    total_amount = perf["total"] or Decimal("0")
    received = perf["received"] or Decimal("0")

    company_target = SalesTarget.objects.filter(
        month=month, scope="COMPANY").aggregate(s=Sum("amount_target"))["s"] or Decimal("0")

    # 部门业绩
    dept_perf = []
    for d in Department.objects.filter(is_deleted=False):
        ids = User.objects.filter(department=d).values_list("id", flat=True)
        agg = contracts.filter(sales_id__in=ids).aggregate(t=Sum("amount"), c=Count("id"))
        tgt = SalesTarget.objects.filter(month=month, scope="DEPARTMENT", department=d)\
            .aggregate(s=Sum("amount_target"))["s"] or Decimal("0")
        amt = agg["t"] or Decimal("0")
        dept_perf.append({
            "department_id": d.id, "department_name": d.name, "code": d.code,
            "amount": float(amt), "orders": agg["c"] or 0,
            "target": float(tgt),
            "completion": round(float(amt) / float(tgt) * 100, 1) if tgt else 0,
        })

    # 员工数
    staff = User.objects.filter(is_active=True, status__in=["PROBATION", "REGULAR", "INTERN"])
    staff_by_dept = {d["department__code"]: d["c"] for d in
                     staff.values("department__code").annotate(c=Count("id"))}

    # 线索
    leads = Lead.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
    lead_stat = {
        "total": leads.count(),
        "dealt": leads.filter(status="DEAL").count(),
        "following": leads.filter(status="FOLLOWING").count(),
        "lost": leads.filter(status="LOST").count(),
    }

    # 考勤（今日）
    today_att = Attendance.objects.filter(date=today)
    att_stat = {
        "total_staff": staff.count(),
        "checked": today_att.exclude(check_in__isnull=True).count(),
        "late": today_att.filter(status="LATE").count(),
        "leave": today_att.filter(status="LEAVE").count(),
        "absent": today_att.filter(status="ABSENT").count(),
    }

    # 会计部做账进度
    tasks = MonthlyTask.objects.filter(period=month, is_deleted=False)
    acc_stat = {
        "total": tasks.count(),
        "done": tasks.filter(status__in=["DECLARED", "DONE"]).count(),
        "overdue": tasks.filter(is_overdue=True).count()
                   or tasks.filter(deadline__lt=today).exclude(status__in=["DECLARED", "DONE"]).count(),
    }
    acc_stat["completion"] = round(acc_stat["done"] / acc_stat["total"] * 100, 1) if acc_stat["total"] else 0

    # 运营投放
    ads = AdDailyStat.objects.filter(date__gte=start, date__lte=end)
    ad_agg = ads.aggregate(cost=Sum("cost"), lead=Sum("lead_count"), deal=Sum("deal_count"),
                           amount=Sum("deal_amount"), wechat=Sum("wechat_added"))
    cost = ad_agg["cost"] or 0
    deal_amount = ad_agg["amount"] or 0
    ops_stat = {
        "cost": float(cost),
        "leads": ad_agg["lead"] or 0,
        "wechat": ad_agg["wechat"] or 0,
        "deals": ad_agg["deal"] or 0,
        "deal_amount": float(deal_amount),
        "cpl": round(float(cost) / ad_agg["lead"], 2) if ad_agg["lead"] else 0,
        "cac": round(float(cost) / ad_agg["deal"], 2) if ad_agg["deal"] else 0,
        "roi": round(float(deal_amount) / float(cost), 2) if cost else 0,
    }

    return Response({"code": 0, "data": {
        "month": month,
        "performance": {
            "amount": float(total_amount),
            "received": float(received),
            "receivable": float(total_amount - received),
            "orders": perf["cnt"] or 0,
            "target": float(company_target),
            "completion": round(float(total_amount) / float(company_target) * 100, 1) if company_target else 0,
        },
        "departments": dept_perf,
        "staff": {"total": staff.count(), "by_department": staff_by_dept},
        "leads": lead_stat,
        "attendance": att_stat,
        "accounting": acc_stat,
        "ops": ops_stat,
    }})


@api_view(["GET"])
def rank(request):
    """业绩排行榜"""
    month = request.query_params.get("month") or _month_str()
    start, end = _month_range(month)
    users = _scope_users(request).select_related("department", "team")

    rows = []
    for u in users:
        agg = Contract.objects.filter(sales=u, signed_date__gte=start, signed_date__lte=end)\
            .aggregate(t=Sum("amount"), c=Count("id"))
        calls = CallRecord.objects.filter(user=u, created_at__date__gte=start,
                                          created_at__date__lte=end).count()
        amount = agg["t"] or Decimal("0")
        target = u.month_target or Decimal("0")
        rows.append({
            "user_id": u.id, "name": u.display_name,
            "department": u.department.name if u.department else "-",
            "team": u.team.name if u.team else "-",
            "amount": float(amount), "orders": agg["c"] or 0,
            "calls": calls,
            "target": float(target),
            "completion": round(float(amount) / float(target) * 100, 1) if target else 0,
        })
    rows.sort(key=lambda x: x["amount"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return Response({"code": 0, "data": rows})


@api_view(["GET"])
def trend(request):
    """近 N 个月业绩趋势"""
    months = int(request.query_params.get("months", 6))
    today = timezone.now().date()
    data = []
    for i in range(months - 1, -1, -1):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12
            y -= 1
        ms = f"{y}-{m:02d}"
        s, e = _month_range(ms)
        agg = Contract.objects.filter(signed_date__gte=s, signed_date__lte=e)\
            .aggregate(t=Sum("amount"), c=Count("id"))
        cost = AdDailyStat.objects.filter(date__gte=s, date__lte=e)\
            .aggregate(c=Sum("cost"))["c"] or 0
        data.append({
            "month": ms,
            "amount": float(agg["t"] or 0),
            "orders": agg["c"] or 0,
            "ad_cost": float(cost),
        })
    return Response({"code": 0, "data": data})


@api_view(["GET"])
def todo(request):
    """我的待办：待审批 / 未交日报 / 逾期任务"""
    u = request.user
    today = timezone.now().date()

    pending_leaves = LeaveApplication.objects.filter(status="PENDING", is_deleted=False)
    if not (u.is_superuser or u.role in ("BOSS", "HR")):
        if u.role == "MANAGER" and u.department_id:
            pending_leaves = pending_leaves.filter(user__department_id=u.department_id)
        elif u.role == "LEADER" and u.team_id:
            pending_leaves = pending_leaves.filter(user__team_id=u.team_id)
        else:
            pending_leaves = pending_leaves.none()

    my_report = DailyReport.objects.filter(user=u, date=today).exists()
    month = _month_str()
    overdue_tasks = MonthlyTask.objects.filter(
        is_deleted=False, deadline__lt=today
    ).exclude(status__in=["DECLARED", "DONE"])
    if u.role == "EMPLOYEE":
        overdue_tasks = overdue_tasks.filter(accountant=u)

    return Response({"code": 0, "data": {
        "pending_approvals": pending_leaves.count(),
        "daily_report_submitted": my_report,
        "overdue_accounting_tasks": overdue_tasks.count(),
        "date": str(today),
    }})


@api_view(["GET"])
def department_detail(request, code):
    """单部门详情看板"""
    month = request.query_params.get("month") or _month_str()
    start, end = _month_range(month)
    dept = Department.objects.filter(code=code, is_deleted=False).first()
    if not dept:
        return Response({"code": 404, "msg": "部门不存在"})
    ids = User.objects.filter(department=dept, is_active=True).values_list("id", flat=True)

    data = {"department": dept.name, "code": code, "month": month, "staff_count": len(ids)}

    if code == "SALES":
        contracts = Contract.objects.filter(sales_id__in=ids, signed_date__gte=start, signed_date__lte=end)
        agg = contracts.aggregate(t=Sum("amount"), c=Count("id"))
        leads = Lead.objects.filter(owner_id__in=ids)
        calls = CallRecord.objects.filter(user_id__in=ids, created_at__date__gte=start,
                                          created_at__date__lte=end)
        data.update({
            "amount": float(agg["t"] or 0), "orders": agg["c"] or 0,
            "lead_total": leads.count(),
            "lead_dealt": leads.filter(status="DEAL").count(),
            "calls": calls.count(),
            "connected": calls.filter(result="CONNECTED").count(),
        })
    elif code == "ACCOUNT":
        tasks = MonthlyTask.objects.filter(period=month, is_deleted=False, accountant_id__in=ids)
        clients = AccountingClient.objects.filter(is_deleted=False, accountant_id__in=ids)
        data.update({
            "task_total": tasks.count(),
            "task_done": tasks.filter(status__in=["DECLARED", "DONE"]).count(),
            "overdue": tasks.filter(deadline__lt=timezone.now().date())
                            .exclude(status__in=["DECLARED", "DONE"]).count(),
            "client_total": clients.count(),
            "client_active": clients.filter(status="ACTIVE").count(),
        })
    elif code == "OPS":
        ads = AdDailyStat.objects.filter(date__gte=start, date__lte=end)
        agg = ads.aggregate(cost=Sum("cost"), lead=Sum("lead_count"), deal=Sum("deal_count"),
                            amount=Sum("deal_amount"), wechat=Sum("wechat_added"),
                            impression=Sum("impression"), click=Sum("click"))
        by_platform = []
        for p in AdPlatform.objects.filter(is_deleted=False):
            pagg = ads.filter(platform=p).aggregate(
                cost=Sum("cost"), lead=Sum("lead_count"), deal=Sum("deal_count"),
                amount=Sum("deal_amount"))
            pc = float(pagg["cost"] or 0)
            pa = float(pagg["amount"] or 0)
            by_platform.append({
                "platform": p.name, "code": p.code,
                "cost": pc, "leads": pagg["lead"] or 0, "deals": pagg["deal"] or 0,
                "amount": pa,
                "cpl": round(pc / pagg["lead"], 2) if pagg["lead"] else 0,
                "roi": round(pa / pc, 2) if pc else 0,
            })
        cost = float(agg["cost"] or 0)
        amount = float(agg["amount"] or 0)
        data.update({
            "cost": cost, "leads": agg["lead"] or 0, "wechat": agg["wechat"] or 0,
            "deals": agg["deal"] or 0, "amount": amount,
            "impression": agg["impression"] or 0, "click": agg["click"] or 0,
            "cpl": round(cost / agg["lead"], 2) if agg["lead"] else 0,
            "cac": round(cost / agg["deal"], 2) if agg["deal"] else 0,
            "roi": round(amount / cost, 2) if cost else 0,
            "by_platform": by_platform,
        })
    return Response({"code": 0, "data": data})


@api_view(["GET"])
def department_members(request, code):
    """部门成员业绩目标与达成进度：按月返回每个成员的月度目标与本月业绩"""
    month = request.query_params.get("month") or _month_str()
    rows, summary = _members_for(code, month)
    if rows is None:
        return Response({"code": 404, "msg": "部门不存在"})
    return Response({"code": 0, "data": rows, "summary": summary})


def _members_for(code, month):
    """返回某部门成员的本月业绩目标与达成（含排名）。部门不存在返回 (None, None)"""
    start, end = _month_range(month)
    dept = Department.objects.filter(code=code, is_deleted=False).first()
    if not dept:
        return None, None

    members = User.objects.filter(
        department=dept, is_active=True,
        status__in=["PROBATION", "REGULAR", "INTERN"],
    ).select_related("department", "team")

    rows = []
    for u in members:
        target = u.month_target or Decimal("0")
        if code == "SALES":
            agg = Contract.objects.filter(
                sales=u, signed_date__gte=start, signed_date__lte=end).aggregate(t=Sum("amount"))
            achieved = agg["t"] or Decimal("0")
            metric = "合同成交额"
        elif code == "ACCOUNT":
            agg = AccountingClient.objects.filter(
                accountant=u, status="ACTIVE").aggregate(f=Sum("monthly_fee"))
            achieved = agg["f"] or Decimal("0")
            metric = "在管客户月服务费"
        elif code == "OPS":
            agg = AdDailyStat.objects.filter(
                operator=u, date__gte=start, date__lte=end).aggregate(a=Sum("deal_amount"))
            achieved = agg["a"] or Decimal("0")
            metric = "投放带来成交额"
        else:
            achieved = Decimal("0")
            metric = "业绩"
        af = float(achieved)
        tf = float(target)
        rows.append({
            "user_id": u.id,
            "name": u.display_name,
            "team": u.team.name if u.team else "-",
            "role": u.get_role_display(),
            "target": tf,
            "achieved": af,
            "metric": metric,
            "completion": round(af / tf * 100, 1) if tf else 0,
        })
    rows.sort(key=lambda x: x["achieved"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    total_target = sum(r["target"] for r in rows)
    total_achieved = sum(r["achieved"] for r in rows)
    summary = {
        "member_count": len(rows),
        "total_target": round(total_target, 2),
        "total_achieved": round(total_achieved, 2),
        "completion": round(total_achieved / total_target * 100, 1) if total_target else 0,
    }
    return rows, summary


def _dept_total(code, month):
    """返回某部门的本月业绩合计与目标完成率（用于权限墙的部门合计卡）"""
    start, end = _month_range(month)
    dept = Department.objects.filter(code=code, is_deleted=False).first()
    if not dept:
        return {"code": code, "name": "", "amount": 0, "target": 0, "completion": 0}
    ids = User.objects.filter(department=dept, is_active=True).values_list("id", flat=True)
    if code == "SALES":
        amt = Contract.objects.filter(
            sales_id__in=ids, signed_date__gte=start, signed_date__lte=end
        ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
    elif code == "ACCOUNT":
        amt = AccountingClient.objects.filter(
            accountant_id__in=ids, status="ACTIVE"
        ).aggregate(f=Sum("monthly_fee"))["f"] or Decimal("0")
    elif code == "OPS":
        amt = AdDailyStat.objects.filter(
            operator_id__in=ids, date__gte=start, date__lte=end
        ).aggregate(a=Sum("deal_amount"))["a"] or Decimal("0")
    else:
        amt = Decimal("0")
    tgt = SalesTarget.objects.filter(
        month=month, scope="DEPARTMENT", department=dept
    ).aggregate(s=Sum("amount_target"))["s"] or Decimal("0")
    amt = float(amt)
    tgt = float(tgt)
    return {
        "code": code,
        "name": dept.name,
        "amount": round(amt, 2),
        "target": round(tgt, 2),
        "completion": round(amt / tgt * 100, 1) if tgt else 0,
    }


@api_view(["GET"])
def data_wall(request):
    """权限隔离墙：按角色返回各部门业绩可见性
    - 老板 / 人事：全部部门 + 成员明细
    - 部门主管 / 组长：本部门成员明细 + 其他部门仅合计
    - 员工：本部门成员明细（看不到其他部门）
    """
    u = request.user
    month = request.query_params.get("month") or _month_str()
    own_code = u.department.code if u.department_id else None
    is_boss = bool(u.is_superuser or u.role in ("BOSS", "HR"))
    # 有效角色：超级管理员/老板/人事统一按 BOSS 视角展示，避免 admin 误显「员工」
    effective_role = "BOSS" if is_boss else (u.role or "EMPLOYEE")

    departments = []
    for d in Department.objects.filter(is_deleted=False):
        total = _dept_total(d.code, month)
        block = {"code": d.code, "name": d.name, "total": total}
        if is_boss or d.code == own_code:
            rows, summary = _members_for(d.code, month)
            block["members"] = rows or []
            block["summary"] = summary
            block["can_see_members"] = True
        else:
            block["members"] = None
            block["can_see_members"] = False
        departments.append(block)

    role_map = {
        "BOSS": "老板/总经理：可见全部部门及每位成员业绩明细",
        "HR": "人事行政：可见全部部门及每位成员业绩明细",
        "MANAGER": "部门主管：可见本部门成员明细 + 其他部门仅合计",
        "LEADER": "组长/主管：可见本部门成员明细 + 其他部门仅合计",
        "EMPLOYEE": "员工：仅可见本部门成员业绩与排名",
    }
    return Response({"code": 0, "data": {
        "role": effective_role,
        "role_desc": role_map.get(effective_role, ""),
        "month": month,
        "own_department": own_code,
        "is_boss": is_boss,
        "departments": departments,
    }})


# ---------------- AI 经营助手 ----------------
import json as _ai_json
import urllib.request as _ai_ureq
import urllib.error as _ai_uerr
from django.conf import settings as _ai_settings


def _ai_snapshot_overview(req):
    """经营总览快照（直接查 DB，避免依赖 view 函数调用）"""
    month = req.query_params.get("month") or timezone.localdate().strftime("%Y-%m")
    start, end = _month_range(month)
    today = timezone.localdate()
    contracts = Contract.objects.filter(signed_date__gte=start, signed_date__lte=end)
    agg = contracts.aggregate(t=Sum("amount"), r=Sum("received"), c=Count("id"))
    amount = float(agg["t"] or 0)
    received = float(agg["r"] or 0)
    target = float(SalesTarget.objects.filter(month=month, scope="COMPANY")
                   .aggregate(s=Sum("amount_target"))["s"] or 0)
    completion = round(amount / target * 100, 1) if target else 0
    ads = AdDailyStat.objects.filter(date__gte=start, date__lte=end)
    aagg = ads.aggregate(cost=Sum("cost"), lead=Sum("lead_count"),
                         deal=Sum("deal_count"), amount=Sum("deal_amount"))
    cost = float(aagg["cost"] or 0)
    deal_amount = float(aagg["amount"] or 0)
    roi = round(deal_amount / cost, 2) if cost else 0
    tasks = MonthlyTask.objects.filter(period=month, is_deleted=False)
    done = tasks.filter(status__in=["DECLARED", "DONE"]).count()
    overdue = tasks.filter(is_overdue=True).count() or \
              tasks.filter(deadline__lt=today).exclude(status__in=["DECLARED", "DONE"]).count()
    # 待审批：基于可见用户
    u = req.user
    pending_leaves = LeaveApplication.objects.filter(status="PENDING", is_deleted=False)
    if not (u.is_superuser or u.role in ("BOSS", "HR")):
        if u.role == "MANAGER" and u.department_id:
            pending_leaves = pending_leaves.filter(user__department_id=u.department_id)
        elif u.role == "LEADER" and u.team_id:
            pending_leaves = pending_leaves.filter(user__team_id=u.team_id)
        else:
            pending_leaves = pending_leaves.none()
    my_report = DailyReport.objects.filter(user=u, date=today).exists()
    return {
        "month": month,
        "performance": {
            "amount": amount, "target": target, "completion": completion,
            "received": received, "orders": agg["c"] or 0,
        },
        "ops": {"roi": roi, "cost": cost,
                "leads": aagg["lead"] or 0, "deals": aagg["deal"] or 0,
                "cpl": round(cost / aagg["lead"], 2) if aagg["lead"] else 0,
                "cac": round(cost / aagg["deal"], 2) if aagg["deal"] else 0},
        "leads": {"total": contracts.count()},
        "accounting": {"total": tasks.count(), "done": done, "overdue": overdue,
                       "completion": round(done / tasks.count() * 100, 1) if tasks.count() else 0},
        "todo": {"pending_approvals": pending_leaves.count(),
                 "overdue_accounting_tasks": overdue,
                 "daily_report_submitted": my_report},
    }


def _ai_snapshot_completion(req):
    p = _ai_snapshot_overview(req)
    perf = p["performance"]
    return {"performance": perf,
            "gap": max((perf.get("target") or 0) - (perf.get("amount") or 0), 0)}


def _ai_snapshot_expiring(req):
    from datetime import timedelta as _td
    from apps.sales.models import Customer as _Customer
    from apps.accounting.models import AccountingClient as _AcClient
    today = timezone.localdate()
    s_qs = _Customer.objects.filter(
        is_deleted=False, expire_at__isnull=False,
        expire_at__gte=today, expire_at__lte=today + _td(days=30)
    ).order_by("expire_at")
    a_qs = _AcClient.objects.filter(
        is_deleted=False, service_end__isnull=False,
        service_end__gte=today, service_end__lte=today + _td(days=60)
    ).order_by("service_end")
    return {
        "sales_30d": {
            "count": s_qs.count(),
            "items": [{"name": x["name"], "expire_at": str(x["expire_at"])}
                      for x in s_qs.values("name", "expire_at")[:10]],
        },
        "acc_60d": {
            "count": a_qs.count(),
            "items": [{"customer_name": x["customer__name"], "service_end": str(x["service_end"])}
                      for x in a_qs.values("customer__name", "service_end")[:10]],
        },
    }


def _ai_snapshot_roi(req):
    snap = _ai_snapshot_overview(req)
    return {"ops": snap["ops"], "month": snap["month"]}


def _ai_snapshot_approval(req):
    snap = _ai_snapshot_overview(req)
    return {"todo": snap["todo"]}


def _ai_snapshot_free(req):
    return _ai_snapshot_overview(req)


_AI_SNAPSHOT_BUILDERS = {
    "overview": _ai_snapshot_overview,
    "completion": _ai_snapshot_completion,
    "expiring": _ai_snapshot_expiring,
    "roi": _ai_snapshot_roi,
    "approval": _ai_snapshot_approval,
    "free": _ai_snapshot_free,
}


def _ai_system_prompt():
    return (
        "你是「财税企管云」的 AI 经营助手，服务于一家代记账/财税服务公司。"
        "你会基于实时业务数据，用简洁、口语化的中文回答老板和高管的经营问题。"
        "回答要求：1) 3-6 行要点式短句；2) 必须包含具体数字；3) 给出明确建议和风险点；"
        "4) 必要时给出可执行的下一步；5) 不要使用 Markdown 代码块，整段纯文本即可。"
    )


def _ai_user_prompt(mode, question, snapshot):
    head = "[用户问题] %s\n[场景] %s\n[实时数据]\n" % (question or "(无)", mode)
    snap_text = _ai_json.dumps(snapshot, ensure_ascii=False, default=str)[:2400]
    return head + snap_text


def _ai_call_llm(base_url, api_key, model, sys_prompt, user_prompt):
    url = base_url.rstrip("/") + "/chat/completions"
    body = _ai_json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 800,
    }).encode("utf-8")
    req = _ai_ureq.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key,
    }, method="POST")
    with _ai_ureq.urlopen(req, timeout=getattr(_ai_settings, "LLM_TIMEOUT", 30)) as resp:
        data = _ai_json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _ai_fmt(n):
    try:
        return "{:,.0f}".format(float(n or 0))
    except Exception:
        return str(n)


def _ai_demo_answer(mode, question, snapshot):
    """无 API Key 或调用失败时的本地模板答案"""
    p = (snapshot or {}).get("performance", {}) or {}
    rate = p.get("completion") or 0
    amount = p.get("amount") or 0
    target = p.get("target") or 0
    ops = (snapshot or {}).get("ops", {}) or {}
    todo = (snapshot or {}).get("todo", {}) or {}
    if mode == "completion":
        tip = "已达标，复盘可复制打法" if rate >= 100 else ("进度过半，加大高意向客户跟进" if rate >= 60 else "进度滞后，建议盘点瓶颈环节")
        return ("🎯 本月业绩完成率 %s%%\n目标 ¥%s，实际 ¥%s，缺口 ¥%s\n状态：%s。"
                % (rate, _ai_fmt(target), _ai_fmt(amount), _ai_fmt(max(target - amount, 0)), tip))
    if mode == "overview":
        return ("📊 %s 经营概览：\n• 业绩 ¥%s / 目标 ¥%s，完成率 %s%%\n"
                "• 投放 ROI %s，线索 %s，成交 %s\n"
                "• 待审批 %s 项，逾期做账 %s 户"
                % (snapshot.get("month", ""), _ai_fmt(amount), _ai_fmt(target), rate,
                   ops.get("roi", 0), ops.get("leads", 0), ops.get("deals", 0),
                   todo.get("pending_approvals", 0), todo.get("overdue_accounting_tasks", 0)))
    if mode == "expiring":
        s = (snapshot or {}).get("sales_30d", {}) or {}
        a = (snapshot or {}).get("acc_60d", {}) or {}
        return ("⏰ 到期预警：\n• 30 天内合同到期 %s 户\n• 60 天内代账到期 %s 户\n"
                "建议 15 天内到期客户优先电话/微信触达，推续费方案。"
                % (s.get("count", 0), a.get("count", 0)))
    if mode == "roi":
        return ("📣 本月投放 ROI %s\n消耗 ¥%s，线索 %s，成交 %s\n"
                "建议优化低 ROI 渠道结构，对高 ROI 渠道加预算。"
                % (ops.get("roi", 0), _ai_fmt(ops.get("cost", 0)), ops.get("leads", 0), ops.get("deals", 0)))
    if mode == "approval":
        n = todo.get("pending_approvals", 0)
        return ("✅ 待审批 %s 项，逾期做账 %s 户。%s"
                % (n, todo.get("overdue_accounting_tasks", 0),
                   "优先处理接近截止的请假与报销。" if n else "团队运转顺畅 👍"))
    return ("🤖 演示模式：你的问题是「%s」。\n当前未配置 LLM_API_KEY，请在 backend/config/settings.py 设置 LLM_API_KEY 激活真模型（默认已配 DeepSeek / Qwen 兼容端点）。\n当前实时数据：业绩 ¥%s / 目标 ¥%s，完成率 %s%%。"
            % (question, _ai_fmt(amount), _ai_fmt(target), rate))


@api_view(["POST"])
def ai_chat(request):
    """AI 经营助手：聚合数据 + 调真 LLM 合成回答。无 Key 时降级为模板回答。"""
    mode = (request.data.get("mode") or "free").strip().lower()
    question = (request.data.get("question") or "").strip()
    builder = _AI_SNAPSHOT_BUILDERS.get(mode, _ai_snapshot_free)
    try:
        snapshot = builder(request)
    except Exception:
        snapshot = {}
    api_key = (getattr(_ai_settings, "LLM_API_KEY", "") or "").strip()
    base_url = (getattr(_ai_settings, "LLM_BASE_URL", "") or "").strip()
    model = getattr(_ai_settings, "LLM_MODEL", "deepseek-chat")
    enabled = bool(api_key and base_url)
    if not enabled:
        return Response({"code": 0, "data": {
            "answer": _ai_demo_answer(mode, question, snapshot),
            "demo": True, "model": model,
            "hint": "未配置 LLM_API_KEY；填入 DeepSeek/Qwen API Key 后即激活真模型",
        }})
    try:
        answer = _ai_call_llm(
            base_url, api_key, model,
            _ai_system_prompt(), _ai_user_prompt(mode, question, snapshot),
        )
        return Response({"code": 0, "data": {
            "answer": answer, "demo": False, "model": model,
        }})
    except _ai_uerr.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="ignore")[:200]
        except Exception:
            pass
        answer = _ai_demo_answer(mode, question, snapshot) + \
                 "\n\n（LLM HTTP %s：%s）" % (e.code, body or e.reason)
        return Response({"code": 0, "data": {
            "answer": answer, "demo": True, "model": model,
            "error": "HTTP %s" % e.code, "hint": body,
        }})
    except Exception as e:
        answer = _ai_demo_answer(mode, question, snapshot) + \
                 "\n\n（LLM 调用异常：%s）" % str(e)[:120]
        return Response({"code": 0, "data": {
            "answer": answer, "demo": True, "model": model,
            "error": str(e)[:200],
        }})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_performance(request):
    """全公司业绩统计：统一全公司（不分部门），含目标与完成率、部门对比、业绩排行"""
    month = request.query_params.get("month") or _month_str()
    start, end = _month_range(month)

    contracts = Contract.objects.filter(signed_date__gte=start, signed_date__lte=end)
    perf = contracts.aggregate(total=Sum("amount"), received=Sum("received"), cnt=Count("id"))
    signed_amount = float(perf["total"] or 0)
    received_amount = float(perf["received"] or 0)
    contract_count = perf["cnt"] or 0

    company_target = float(
        SalesTarget.objects.filter(month=month, scope="COMPANY").aggregate(s=Sum("amount_target"))["s"] or 0
    )

    def _rate(signed, target):
        target = float(target or 0)
        return round(signed / target * 100, 1) if target else 0.0

    departments = []
    for code, name in [("SALES", "电销部"), ("ACCOUNT", "会计部"), ("OPS", "运营部")]:
        dc = contracts.filter(sales__department__code=code)
        d = dc.aggregate(total=Sum("amount"), received=Sum("received"))
        d_target = float(
            SalesTarget.objects.filter(month=month, scope="DEPARTMENT", department__code=code)
            .aggregate(s=Sum("amount_target"))["s"] or 0
        )
        member_count = User.objects.filter(department__code=code, is_active=True).count()
        departments.append({
            "code": code,
            "name": name,
            "signed_amount": float(d["total"] or 0),
            "received_amount": float(d["received"] or 0),
            "target_amount": d_target,
            "completion_rate": _rate(float(d["total"] or 0), d_target),
            "member_count": member_count,
        })

    top_rows = (
        contracts.values("sales")
        .annotate(signed_amount=Sum("amount"))
        .order_by("-signed_amount")[:10]
    )
    top_performers = []
    for r in top_rows:
        uid = r["sales"]
        if not uid:
            continue
        u = User.objects.filter(id=uid).first()
        if not u:
            continue
        dept_name = u.department.name if u.department else "-"
        ptarget = float(
            SalesTarget.objects.filter(month=month, scope="PERSON", user_id=uid)
            .aggregate(s=Sum("amount_target"))["s"] or 0
        )
        top_performers.append({
            "id": uid,
            "name": u.get_full_name() or u.username,
            "department": dept_name,
            "signed_amount": float(r["signed_amount"] or 0),
            "completion_rate": _rate(float(r["signed_amount"] or 0), ptarget),
        })

    return Response({
        "month": month,
        "company": {
            "signed_amount": signed_amount,
            "received_amount": received_amount,
            "contract_count": contract_count,
            "target_amount": company_target,
            "completion_rate": _rate(signed_amount, company_target),
        },
        "departments": departments,
        "top_performers": top_performers,
    })
