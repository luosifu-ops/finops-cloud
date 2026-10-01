"""入职培训模块视图：企业文化 / 制度 / 知识库 / 题库考试 / 入职资料"""
import random

from django.utils import timezone
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.common.permissions import IsHR, IsLeaderOrAbove
from apps.accounts.models import User, Department
from .models import (
    CultureArticle, Regulation, RegulationAck, KnowledgeCategory, KnowledgeArticle,
    LearningRecord, QuestionBank, Question, Exam, ExamRecord,
    OnboardingProfile, OnboardingTask, OnboardingTaskRecord,
)
from .serializers import (
    CultureArticleSerializer, RegulationSerializer, RegulationAckSerializer,
    KnowledgeCategorySerializer, KnowledgeArticleSerializer, LearningRecordSerializer,
    QuestionBankSerializer, QuestionSerializer, QuestionListSerializer,
    ExamSerializer, ExamRecordSerializer,
    OnboardingProfileSerializer, OnboardingTaskSerializer, OnboardingTaskRecordSerializer,
)

# 可自动判分的题型（单选 / 多选 / 判断）
AUTO_JUDGE_TYPES = ("SINGLE", "MULTI", "JUDGE")
# 需人工批改的题型（填空 / 简答）
MANUAL_JUDGE_TYPES = ("FILL", "ESSAY")


def _normalize_answer(qtype, value):
    """标准化答案：去空格、转大写；多选题按字符排序后比较（须完全一致）"""
    text = str(value or "").strip().upper().replace(" ", "")
    if qtype == "MULTI":
        return "".join(sorted(text))
    return text


def _current_profile(user):
    """当前用户的入职资料（优先按转正绑定账号匹配，其次按手机号匹配）"""
    qs = OnboardingProfile.objects.filter(is_deleted=False)
    condition = Q(bound_user=user)
    if user.phone:
        condition = condition | Q(phone=user.phone)
    return qs.filter(condition).order_by("-created_at").first()


class CultureArticleViewSet(viewsets.ModelViewSet):
    """企业文化：列表 / 详情，支持按分类过滤、按标题搜索"""
    queryset = CultureArticle.objects.filter(is_deleted=False)
    serializer_class = CultureArticleSerializer
    search_fields = ["title"]
    ordering_fields = ["sort", "view_count", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        category = params.get("category")
        if category:
            qs = qs.filter(category=category)
        if params.get("is_published") in ("true", "True", "1"):
            qs = qs.filter(is_published=True)
        return qs

    @action(detail=True, methods=["post"])
    def view(self, request, pk=None):
        """阅读量 +1"""
        article = self.get_object()
        article.view_count = (article.view_count or 0) + 1
        article.save(update_fields=["view_count"])
        return Response({"code": 0, "msg": "ok", "data": {"view_count": article.view_count}})


class RegulationViewSet(viewsets.ModelViewSet):
    """公司制度：列表 / 详情，支持按分类过滤"""
    queryset = Regulation.objects.filter(is_deleted=False)
    serializer_class = RegulationSerializer
    search_fields = ["title"]
    ordering_fields = ["created_at", "effective_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        category = params.get("category")
        if category:
            qs = qs.filter(category=category)
        if params.get("is_published") in ("true", "True", "1"):
            qs = qs.filter(is_published=True)
        return qs

    @action(detail=True, methods=["post"])
    def ack(self, request, pk=None):
        """已读确认（幂等：重复提交不会产生多条记录）"""
        regulation = self.get_object()
        ack, created = RegulationAck.objects.get_or_create(regulation=regulation, user=request.user)
        return Response({"code": 0, "msg": "ok", "data": {
            "regulation_id": regulation.id,
            "created": created,
            "read_at": ack.read_at,
        }})

    @action(detail=False, methods=["get"], url_path="my-acks")
    def my_acks(self, request):
        """我已确认的制度 id 列表"""
        ids = list(RegulationAck.objects.filter(user=request.user)
                   .values_list("regulation_id", flat=True))
        return Response({"code": 0, "msg": "ok", "data": {"regulation_ids": ids, "count": len(ids)}})


class KnowledgeCategoryViewSet(viewsets.ModelViewSet):
    """知识分类树"""
    queryset = KnowledgeCategory.objects.filter(is_deleted=False)
    serializer_class = KnowledgeCategorySerializer
    search_fields = ["name"]
    ordering_fields = ["sort", "id"]

    def get_queryset(self):
        qs = super().get_queryset()
        parent = self.request.query_params.get("parent")
        if parent in ("", "0", "null"):
            qs = qs.filter(parent__isnull=True)
        elif parent:
            qs = qs.filter(parent_id=parent)
        return qs


class KnowledgeArticleViewSet(viewsets.ModelViewSet):
    """知识文章：按分类、难度过滤，按标题、标签搜索"""
    queryset = KnowledgeArticle.objects.filter(is_deleted=False)
    serializer_class = KnowledgeArticleSerializer
    search_fields = ["title", "tags"]
    ordering_fields = ["sort", "view_count", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        category = params.get("category")
        if category:
            qs = qs.filter(category=category)
        level = params.get("level")
        if level:
            qs = qs.filter(level=level)
        knowledge_category = params.get("knowledge_category")
        if knowledge_category:
            qs = qs.filter(knowledge_category_id=knowledge_category)
        if params.get("is_published") in ("true", "True", "1"):
            qs = qs.filter(is_published=True)
        return qs

    def retrieve(self, request, *args, **kwargs):
        """查看详情时阅读量 +1"""
        article = self.get_object()
        article.view_count = (article.view_count or 0) + 1
        article.save(update_fields=["view_count"])
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def learn(self, request, pk=None):
        """提交学习进度：finished 是否完成，duration 学习时长(秒)"""
        article = self.get_object()
        finished = str(request.data.get("finished", "false")).lower() in ("1", "true", "yes")
        try:
            duration = int(request.data.get("duration") or 0)
        except (TypeError, ValueError):
            duration = 0
        record, _ = LearningRecord.objects.get_or_create(user=request.user, article=article)
        record.finished = record.finished or finished
        record.duration = (record.duration or 0) + duration
        record.save()
        return Response({"code": 0, "msg": "ok",
                         "data": LearningRecordSerializer(record).data})

    @action(detail=False, methods=["get"], url_path="my-progress")
    def my_progress(self, request):
        """我的学习统计：必修总数、已完成数、完成率"""
        total = KnowledgeArticle.objects.filter(
            is_deleted=False, is_published=True, is_required=True).count()
        finished = LearningRecord.objects.filter(
            user=request.user, finished=True,
            article__is_deleted=False, article__is_required=True).count()
        rate = round(finished / total * 100, 1) if total else 0.0
        return Response({"code": 0, "msg": "ok", "data": {
            "required_total": total,
            "finished_count": finished,
            "completion_rate": rate,
        }})


class QuestionBankViewSet(viewsets.ModelViewSet):
    """题库"""
    queryset = QuestionBank.objects.filter(is_deleted=False)
    serializer_class = QuestionBankSerializer
    search_fields = ["name"]


class QuestionViewSet(viewsets.ModelViewSet):
    """题目：按题库过滤；员工(EMPLOYEE)不返回正确答案"""
    queryset = Question.objects.filter(is_deleted=False)
    serializer_class = QuestionSerializer
    search_fields = ["stem"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        bank = params.get("bank")
        if bank:
            qs = qs.filter(bank_id=bank)
        qtype = params.get("qtype")
        if qtype:
            qs = qs.filter(qtype=qtype)
        level = params.get("level")
        if level:
            qs = qs.filter(level=level)
        return qs

    def get_serializer_class(self):
        """员工端一律使用不含答案的列表序列化器"""
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated and user.role == "EMPLOYEE":
            return QuestionListSerializer
        return QuestionSerializer


class ExamViewSet(viewsets.ModelViewSet):
    """考试：开始考试、提交答卷、我的记录、排行榜"""
    queryset = Exam.objects.filter(is_deleted=False)
    serializer_class = ExamSerializer
    search_fields = ["title"]
    ordering_fields = ["created_at", "start_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        status_value = params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        bank = params.get("bank")
        if bank:
            qs = qs.filter(bank_id=bank)
        return qs

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """开始考试：按抽题数量随机出题，创建考试记录"""
        exam = self.get_object()
        user = request.user
        now = timezone.now()
        if exam.status != "PUBLISHED":
            return Response({"code": 1, "msg": "考试未发布，无法开始"},
                            status=status.HTTP_400_BAD_REQUEST)
        if exam.start_at and now < exam.start_at:
            return Response({"code": 1, "msg": "考试尚未开放"},
                            status=status.HTTP_400_BAD_REQUEST)
        if exam.end_at and now > exam.end_at:
            return Response({"code": 1, "msg": "考试已截止"},
                            status=status.HTTP_400_BAD_REQUEST)

        used = ExamRecord.objects.filter(exam=exam, user=user).count()
        attempt = used + 1
        if used >= exam.max_attempts:
            return Response({"code": 1, "msg": f"考试次数已用完（最多 {exam.max_attempts} 次）"},
                            status=status.HTTP_400_BAD_REQUEST)
        if used > 0 and not exam.allow_retake:
            return Response({"code": 1, "msg": "该考试不允许重考"},
                            status=status.HTTP_400_BAD_REQUEST)

        pool = Question.objects.filter(is_deleted=False)
        if exam.bank_id:
            pool = pool.filter(bank_id=exam.bank_id)
        pool = list(pool)
        if not pool:
            return Response({"code": 1, "msg": "题库暂无题目，无法组卷"},
                            status=status.HTTP_400_BAD_REQUEST)
        count = min(exam.question_count or len(pool), len(pool))
        picked = random.sample(pool, count)

        record = ExamRecord.objects.create(
            exam=exam, user=user, attempt=attempt,
            answers={"question_ids": [q.id for q in picked]},
        )
        return Response({"code": 0, "msg": "ok", "data": {
            "record_id": record.id,
            "attempt": attempt,
            "duration": exam.duration,
            "questions": QuestionListSerializer(picked, many=True).data,
        }})

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """提交答卷并自动判分：answers 形如 {"12":"A","13":"AB"}"""
        exam = self.get_object()
        record_id = request.data.get("record_id")
        answers = request.data.get("answers") or {}
        if not isinstance(answers, dict):
            return Response({"code": 1, "msg": "answers 格式不正确"},
                            status=status.HTTP_400_BAD_REQUEST)
        record = ExamRecord.objects.filter(id=record_id, exam=exam, user=request.user).first()
        if not record:
            return Response({"code": 1, "msg": "考试记录不存在"},
                            status=status.HTTP_404_NOT_FOUND)
        if record.submitted_at:
            return Response({"code": 1, "msg": "该答卷已提交，不能重复提交"},
                            status=status.HTTP_400_BAD_REQUEST)

        question_ids = record.answers.get("question_ids") if isinstance(record.answers, dict) else None
        if not question_ids:
            question_ids = list(answers.keys())
        question_ids = [int(qid) for qid in question_ids]
        qmap = {q.id: q for q in Question.objects.filter(id__in=question_ids)}

        score = 0
        pending = []
        for qid in question_ids:
            question = qmap.get(qid)
            if not question:
                continue
            if question.qtype in AUTO_JUDGE_TYPES:
                user_answer = answers.get(str(qid), answers.get(qid, ""))
                if _normalize_answer(question.qtype, user_answer) == _normalize_answer(
                        question.qtype, question.answer):
                    score += question.score or 0
            elif question.qtype in MANUAL_JUDGE_TYPES:
                pending.append(qid)

        record.answers = {"question_ids": question_ids, "answers": answers, "pending": pending}
        record.score = score
        record.passed = score >= exam.pass_score
        record.submitted_at = timezone.now()
        record.save()
        return Response({"code": 0, "msg": "ok", "data": {
            "record_id": record.id,
            "score": record.score,
            "passed": record.passed,
            "pass_score": exam.pass_score,
            "pending_count": len(pending),
            "pending_questions": pending,
        }})

    @action(detail=False, methods=["get"], url_path="my-records")
    def my_records(self, request):
        """我的考试记录"""
        qs = ExamRecord.objects.filter(user=request.user).select_related("exam")
        exam_id = request.query_params.get("exam")
        if exam_id:
            qs = qs.filter(exam_id=exam_id)
        return Response({"code": 0, "msg": "ok", "data": ExamRecordSerializer(qs, many=True).data})

    @action(detail=True, methods=["get"], permission_classes=[IsLeaderOrAbove])
    def rank(self, request, pk=None):
        """考试成绩排行榜（仅主管及以上可见）"""
        exam = self.get_object()
        qs = ExamRecord.objects.filter(
            exam=exam, submitted_at__isnull=False
        ).select_related("user").order_by("-score", "submitted_at")[:50]
        data = [{
            "record_id": r.id,
            "user_id": r.user_id,
            "user_name": r.user.display_name,
            "score": r.score,
            "passed": r.passed,
            "attempt": r.attempt,
            "submitted_at": r.submitted_at,
        } for r in qs]
        return Response({"code": 0, "msg": "ok", "data": data})

    @action(detail=False, methods=["get"], url_path="my-wrong-book")
    def my_wrong_book(self, request):
        """我的错题本：汇总当前用户所有已提交答卷中答错的客观题（去重）"""
        records = ExamRecord.objects.filter(user=request.user, submitted_at__isnull=False)
        rec_map = []
        all_qids = []
        for rec in records:
            answers = rec.answers or {}
            qids = answers.get("question_ids") or []
            rec_map.append((rec, answers))
            all_qids.extend(qids)
        qmap = {q.id: q for q in Question.objects.filter(id__in=all_qids)}
        wrong = []
        seen = set()
        for rec, answers in rec_map:
            user_answers = answers.get("answers") or {}
            for qid in answers.get("question_ids") or []:
                q = qmap.get(qid)
                if not q or q.qtype in MANUAL_JUDGE_TYPES:
                    continue
                ua = user_answers.get(str(qid), "")
                if _normalize_answer(q.qtype, ua) == _normalize_answer(q.qtype, q.answer):
                    continue
                key = (rec.exam_id, qid)
                if key in seen:
                    continue
                seen.add(key)
                wrong.append({
                    "question_id": qid,
                    "exam_title": rec.exam.title,
                    "qtype": q.qtype,
                    "qtype_name": q.get_qtype_display(),
                    "stem": q.stem,
                    "options": q.options,
                    "my_answer": ua,
                    "correct_answer": q.answer,
                    "analysis": q.analysis,
                    "error_count": 1,
                })
        return Response({"code": 0, "msg": "ok", "data": wrong})

    @action(detail=True, methods=["get"])
    def wrong_questions(self, request, pk=None):
        """某场考试的错题（取当前用户最新一次已提交答卷）"""
        exam = self.get_object()
        rec = ExamRecord.objects.filter(
            exam=exam, user=request.user, submitted_at__isnull=False
        ).order_by("-submitted_at").first()
        if not rec:
            return Response({"code": 0, "msg": "ok", "data": []})
        answers = rec.answers or {}
        qids = answers.get("question_ids") or []
        user_answers = answers.get("answers") or {}
        qmap = {q.id: q for q in Question.objects.filter(id__in=qids)}
        wrong = []
        for qid in qids:
            q = qmap.get(qid)
            if not q or q.qtype in MANUAL_JUDGE_TYPES:
                continue
            ua = user_answers.get(str(qid), "")
            if _normalize_answer(q.qtype, ua) == _normalize_answer(q.qtype, q.answer):
                continue
            wrong.append({
                "question_id": qid,
                "exam_title": exam.title,
                "qtype": q.qtype,
                "qtype_name": q.get_qtype_display(),
                "stem": q.stem,
                "options": q.options,
                "my_answer": ua,
                "correct_answer": q.answer,
                "analysis": q.analysis,
                "error_count": 1,
            })
        return Response({"code": 0, "msg": "ok", "data": wrong})

    @action(detail=False, methods=["get"], url_path=r"records/(?P<record_id>\d+)")
    def record_detail(self, request, record_id=None):
        """答卷逐题明细：题干 / 我的答案 / 正确答案 / 解析 / 是否正确"""
        rec = get_object_or_404(ExamRecord, id=record_id, user=request.user)
        answers = rec.answers or {}
        qids = answers.get("question_ids") or []
        user_answers = answers.get("answers") or {}
        pending = set(answers.get("pending") or [])
        qmap = {q.id: q for q in Question.objects.filter(id__in=qids)}
        detail = []
        for qid in qids:
            q = qmap.get(qid)
            if not q:
                continue
            ua = user_answers.get(str(qid), "")
            if q.qtype in AUTO_JUDGE_TYPES:
                is_correct = _normalize_answer(q.qtype, ua) == _normalize_answer(q.qtype, q.answer)
            else:
                is_correct = None
            detail.append({
                "qtype": q.qtype,
                "qtype_name": q.get_qtype_display(),
                "stem": q.stem,
                "options": q.options,
                "my_answer": ua,
                "correct_answer": q.answer,
                "analysis": q.analysis,
                "is_correct": is_correct,
                "is_pending": qid in pending,
            })
        data = ExamRecordSerializer(rec).data
        data["detail"] = detail
        return Response({"code": 0, "msg": "ok", "data": data})

class OnboardingProfileViewSet(viewsets.ModelViewSet):
    """入职资料：员工提交、HR/老板审核"""
    queryset = OnboardingProfile.objects.filter(is_deleted=False)
    serializer_class = OnboardingProfileSerializer
    search_fields = ["name", "phone"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        status_value = params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        department = params.get("department")
        if department:
            qs = qs.filter(department_id=department)
        return qs

    @action(detail=False, methods=["post", "put"])
    def submit(self, request):
        """提交入职资料（当前用户）：已存在则更新，不存在则创建"""
        data = request.data
        profile = _current_profile(request.user)
        if profile:
            serializer = self.get_serializer(profile, data=data, partial=True)
        else:
            serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        if instance.status == "DRAFT":
            instance.status = "SUBMITTED"
            instance.save(update_fields=["status"])
        return Response({"code": 0, "msg": "提交成功",
                         "data": OnboardingProfileSerializer(instance, context=self.get_serializer_context()).data})

    @action(detail=True, methods=["post"], permission_classes=[IsHR])
    def review(self, request, pk=None):
        """审核入职资料：action=approve/reject，remark=审核意见"""
        profile = self.get_object()
        operate = (request.data.get("action") or "").lower()
        remark = request.data.get("remark") or ""
        if operate == "approve":
            profile.status = "APPROVED"
        elif operate == "reject":
            profile.status = "REJECTED"
        else:
            return Response({"code": 1, "msg": "action 只能是 approve 或 reject"},
                            status=status.HTTP_400_BAD_REQUEST)
        profile.review_by = request.user
        profile.review_at = timezone.now()
        profile.review_remark = remark
        profile.save(update_fields=["status", "review_by", "review_at", "review_remark"])
        return Response({"code": 0, "msg": "审核完成", "data": {
            "id": profile.id,
            "status": profile.status,
            "status_name": profile.get_status_display(),
            "review_remark": profile.review_remark,
        }})

    @action(detail=False, methods=["get"])
    def my(self, request):
        """我的入职资料"""
        profile = _current_profile(request.user)
        data = OnboardingProfileSerializer(
            profile, context=self.get_serializer_context()).data if profile else None
        return Response({"code": 0, "msg": "ok", "data": data})


class OnboardingTaskViewSet(viewsets.ModelViewSet):
    """入职任务清单：任务维护 + 我的任务完成情况"""
    queryset = OnboardingTask.objects.filter(is_deleted=False)
    serializer_class = OnboardingTaskSerializer
    search_fields = ["title"]
    ordering_fields = ["sort", "id"]

    def get_queryset(self):
        qs = super().get_queryset()
        task_type = self.request.query_params.get("task_type")
        if task_type:
            qs = qs.filter(task_type=task_type)
        return qs

    @action(detail=False, methods=["get"], url_path="my-tasks")
    def my_tasks(self, request):
        """我的入职任务清单及完成状态（自动比对学习/制度/考试/资料记录）"""
        user = request.user
        tasks = list(self.get_queryset())
        ack_ids = set(RegulationAck.objects.filter(
            user=user, regulation_id__isnull=False).values_list("regulation_id", flat=True))
        finished_article_ids = set(LearningRecord.objects.filter(
            user=user, finished=True).values_list("article_id", flat=True))
        passed_exam_ids = set(ExamRecord.objects.filter(
            user=user, passed=True).values_list("exam_id", flat=True))
        profile = _current_profile(user)
        material_done = bool(profile and profile.status in ("SUBMITTED", "APPROVED"))
        records = {r.task_id: r for r in OnboardingTaskRecord.objects.filter(user=user, task__in=tasks)}

        data = []
        for task in tasks:
            record = records.get(task.id)
            if task.task_type == "REGULATION":
                done = bool(task.regulation_id and task.regulation_id in ack_ids)
            elif task.task_type == "COURSE":
                done = bool(task.article_id and task.article_id in finished_article_ids)
            elif task.task_type == "EXAM":
                done = bool(task.exam_id and task.exam_id in passed_exam_ids)
            elif task.task_type == "MATERIAL":
                done = material_done
            else:
                done = bool(record and record.finished)
            if done and record and not record.finished:
                record.finished = True
                record.finished_at = timezone.now()
                record.save(update_fields=["finished", "finished_at"])
            data.append({
                "id": task.id,
                "title": task.title,
                "task_type": task.task_type,
                "task_type_name": task.get_task_type_display(),
                "description": task.description,
                "due_days": task.due_days,
                "required": task.required,
                "sort": task.sort,
                "regulation_id": task.regulation_id,
                "article_id": task.article_id,
                "exam_id": task.exam_id,
                "finished": done,
                "finished_at": record.finished_at if record else None,
            })
        total = len(data)
        finished_count = sum(1 for item in data if item["finished"])
        return Response({"code": 0, "msg": "ok", "data": {
            "total": total,
            "finished_count": finished_count,
            "completion_rate": round(finished_count / total * 100, 1) if total else 0.0,
            "tasks": data,
        }})

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """标记任务完成"""
        task = self.get_object()
        record, _ = OnboardingTaskRecord.objects.get_or_create(user=request.user, task=task)
        record.finished = True
        record.finished_at = timezone.now()
        record.save(update_fields=["finished", "finished_at"])
        return Response({"code": 0, "msg": "ok",
                         "data": OnboardingTaskRecordSerializer(record).data})

    @action(detail=False, methods=["get"])
    def stat(self, request):
        """全员入职任务完成统计（HR/老板视角）"""
        users = User.objects.filter(is_active=True)
        tasks_total = self.get_queryset().count()
        records = OnboardingTaskRecord.objects.filter(task__in=self.get_queryset(), finished=True)
        done_map = {}
        for rec in records.values_list("user_id"):
            done_map[rec[0]] = done_map.get(rec[0], 0) + 1
        data = []
        for u in users:
            finished = done_map.get(u.id, 0)
            dept = u.department.name if getattr(u, "department", None) else "—"
            data.append({
                "user_id": u.id,
                "name": getattr(u, "name", None) or u.username,
                "department_name": dept,
                "total": tasks_total,
                "finished_count": finished,
                "completion_rate": round(finished / tasks_total * 100, 1) if tasks_total else 0.0,
            })
        return Response({"code": 0, "msg": "ok", "data": data})
