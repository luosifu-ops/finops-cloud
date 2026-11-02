"""团队汇总自动聚合（2026-10-30 新增）

口径：
  - 日报汇总：按「日期」聚合当天已提交的日报
  - 周报汇总：按「年-周（ISO）」聚合该周已提交的周报
  - 月报汇总：按「月份」聚合该月已提交的月报
  - 范围：提交人所属部门；若提交人挂在小组上，则按「部门 + 小组」单独成表（小组长看本组）
  - 人工编辑保护：汇总被主管编辑过（is_edited=True）后，自动汇总只刷新统计与来源，
    不再覆盖正文；主管可点「重新生成」强制按最新汇报重建。
"""
from .models import DailyReport, WeeklyReport, MonthlyReport, TeamSummary

KIND_LABEL = {"DAILY": "日报", "WEEKLY": "周报", "MONTHLY": "月报"}
LABEL_KIND = {v: k for k, v in KIND_LABEL.items()}

# 数值型字段的中文名（汇总统计里直接展示）
STAT_LABELS = {
    "calls": "通话数", "wechat": "加微数", "deal": "成交数", "visit": "到访数",
    "leads": "线索数", "follow": "跟进数", "amount": "金额", "orders": "订单数",
}


def period_of(kind, inst):
    """从汇报实例推出周期键"""
    if kind == "DAILY":
        return str(getattr(inst, "date", "") or "")
    if kind == "WEEKLY":
        year = getattr(inst, "year", None)
        week = getattr(inst, "week", None)
        if not year or not week:
            return ""
        return f"{year}-W{int(week):02d}"
    if kind == "MONTHLY":
        return str(getattr(inst, "month", "") or "")
    return ""


def _scope_kwargs(department, team):
    kw = {}
    if department is not None:
        kw["user__department"] = department
    if team is not None:
        kw["user__team"] = team
    return kw


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _merge_stats(target, data):
    """把汇报里的 JSON 数据按数值累加（非数值键忽略）"""
    if not isinstance(data, dict):
        return
    for key, value in data.items():
        f = _num(value)
        if f is None:
            continue
        target[key] = round(target.get(key, 0) + f, 2)


def _fmt_stats(stats):
    if not stats:
        return ""
    parts = []
    for key, value in stats.items():
        label = STAT_LABELS.get(key, key)
        if float(value).is_integer():
            parts.append(f"{label} {int(value)}")
        else:
            parts.append(f"{label} {value}")
    return "、".join(parts)


def _pick(kind, period, department, team):
    """取出该周期内已提交的汇报（按人聚合）"""
    kw = _scope_kwargs(department, team)
    out = []
    if kind == "DAILY":
        qs = DailyReport.objects.filter(
            is_deleted=False, date=period, status__in=["SUBMITTED", "REVIEWED"], **kw
        ).select_related("user", "user__department", "user__team").order_by("user_id")
        for r in qs:
            out.append({
                "id": r.id,
                "who": r.user.display_name if r.user else "",
                "position": getattr(r.user, "position", "") or "",
                "data": r.today_data,
                "lines": [
                    ("今日完成", r.today_done), ("遇到问题", r.problems),
                    ("明日计划", r.tomorrow_plan), ("需要支持", r.need_help),
                ],
            })
    elif kind == "WEEKLY":
        if "-W" not in (period or ""):
            return out
        from django.db.models import Q
        year, week = period.split("-W")
        qs = WeeklyReport.objects.filter(
            is_deleted=False, year=int(year), week=int(week),
            # 周报无 status 字段：填了总结或已落提交时间即视为已提交
            **kw
        ).filter(Q(submitted_at__isnull=False) | ~Q(summary="")
                 ).select_related("user", "user__department", "user__team").order_by("user_id")
        for r in qs:
            out.append({
                "id": r.id,
                "who": r.user.display_name if r.user else "",
                "position": getattr(r.user, "position", "") or "",
                "data": r.data,
                "lines": [
                    ("本周总结", r.summary), ("下周计划", r.next_plan),
                    ("问题与建议", r.problems),
                ],
            })
    elif kind == "MONTHLY":
        from django.db.models import Q
        qs = MonthlyReport.objects.filter(
            is_deleted=False, month=period, **kw
        ).filter(Q(submitted_at__isnull=False) | ~Q(summary="")
                 ).select_related("user", "user__department", "user__team").order_by("user_id")
        for r in qs:
            extra = ""
            if r.target:
                rate = round(float(r.performance or 0) / float(r.target) * 100, 1)
                extra = f"业绩 {r.performance} / 目标 {r.target}（完成 {rate}%）"
            else:
                extra = f"业绩 {r.performance}"
            out.append({
                "id": r.id,
                "who": r.user.display_name if r.user else "",
                "position": getattr(r.user, "position", "") or "",
                "data": r.data,
                "lines": [
                    ("本月总结", r.summary), ("业绩情况", extra),
                    ("下月计划", r.next_plan), ("自我复盘", r.self_review),
                ],
            })
    return out


def _build_content(kind, period, department, team, rows, member_total):
    dept_name = getattr(department, "name", "") or "全公司"
    team_name = getattr(team, "name", "") or ""
    scope = f"{dept_name}{('·' + team_name) if team_name else ''}"
    label = KIND_LABEL.get(kind, "汇报")
    head = (f"【{scope} · {label}汇总】周期 {period}｜"
            f"已提交 {len(rows)} 人 / 在职 {member_total} 人")
    if not rows:
        return head + "\n\n本周期暂无已提交的" + label + "。"
    blocks = [head, ""]
    for idx, row in enumerate(rows, 1):
        who = row["who"] or "未命名"
        pos = f"（{row['position']}）" if row["position"] else ""
        blocks.append(f"{idx}. {who}{pos}")
        for key, value in row["lines"]:
            text = (value or "").strip()
            if text:
                blocks.append(f"   {key}：{text}")
        blocks.append("")
    return "\n".join(blocks).rstrip()


def _member_total(department, team):
    from apps.accounts.models import User
    qs = User.objects.filter(is_active=True)
    if department is not None:
        qs = qs.filter(department=department)
    if team is not None:
        qs = qs.filter(team=team)
    return qs.count()


def rebuild(kind, period, department=None, team=None, force=False):
    """按当前汇报数据重建（或创建）一份团队汇总

    force=True 时忽略人工编辑，强制用最新汇报覆盖正文并解除「已编辑」标记。
    """
    if not kind or not period:
        return None
    rows = _pick(kind=kind, period=period, department=department, team=team)
    member_total = _member_total(department, team)

    stats = {}
    for row in rows:
        _merge_stats(stats, row["data"])

    dept_name = getattr(department, "name", "") or "全公司"
    team_name = getattr(team, "name", "") or ""
    title = f"{dept_name}{('·' + team_name) if team_name else ''} · {period} {KIND_LABEL.get(kind, '')}汇总"

    summary, _created = TeamSummary.objects.get_or_create(
        kind=kind, period=period, department=department, team=team,
        defaults={"title": title},
    )
    summary.title = title
    summary.member_total = member_total
    summary.submitted_total = len(rows)
    summary.stats = stats
    summary.source_ids = [row["id"] for row in rows]
    if force or not summary.is_edited:
        summary.content = _build_content(kind, period, department, team, rows, member_total)
        if force:
            summary.is_edited = False
            summary.edited_by = None
            summary.edited_at = None
    summary.save()
    return summary


def aggregate_report(inst, kind_label):
    """汇报提交后的自动汇总入口（失败不影响汇报保存）"""
    kind = LABEL_KIND.get(kind_label)
    if not kind:
        return None
    user = getattr(inst, "user", None)
    if user is None:
        return None
    period = period_of(kind, inst)
    if not period:
        return None
    department = getattr(user, "department", None)
    if department is None:
        return None
    team = getattr(user, "team", None)
    return rebuild(kind, period, department, team)


def rebuild_all(limit_days=180):
    """全量回填：把所有历史已提交汇报按周期补生成汇总（迁移 / 运维用）"""
    from datetime import timedelta
    from django.utils import timezone

    made = 0
    since = timezone.localdate() - timedelta(days=limit_days)
    combos = set()

    for r in DailyReport.objects.filter(is_deleted=False, date__gte=since,
                                        status__in=["SUBMITTED", "REVIEWED"]):
        combos.add(("DAILY", str(r.date), r.user.department_id, r.user.team_id))
    for r in WeeklyReport.objects.filter(is_deleted=False):
        combos.add(("WEEKLY", f"{r.year}-W{int(r.week):02d}", r.user.department_id, r.user.team_id))
    for r in MonthlyReport.objects.filter(is_deleted=False):
        combos.add(("MONTHLY", r.month, r.user.department_id, r.user.team_id))

    from apps.accounts.models import Department, Team
    for kind, period, dept_id, team_id in combos:
        dept = Department.objects.filter(id=dept_id).first() if dept_id else None
        if dept is None:
            continue
        team = Team.objects.filter(id=team_id).first() if team_id else None
        rebuild(kind, period, dept, team)
        made += 1
    return made
