"""入职培训模块序列化器"""
from rest_framework import serializers
from .models import (
    CultureArticle, Regulation, RegulationAck, KnowledgeCategory, KnowledgeArticle,
    LearningRecord, QuestionBank, Question, Exam, ExamRecord,
    OnboardingProfile, OnboardingTask, OnboardingTaskRecord,
)


class CultureArticleSerializer(serializers.ModelSerializer):
    """企业文化文章"""
    category_name = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = CultureArticle
        fields = ["id", "title", "category", "category_name", "cover", "content",
                  "video_url", "is_published", "sort", "view_count", "created_at"]
        read_only_fields = ["view_count", "created_at"]


class RegulationSerializer(serializers.ModelSerializer):
    """公司制度"""
    category_name = serializers.CharField(source="get_category_display", read_only=True)
    acked = serializers.SerializerMethodField()

    class Meta:
        model = Regulation
        fields = ["id", "title", "category", "category_name", "version", "content",
                  "attachment", "effective_date", "is_published", "must_read",
                  "acked", "created_at"]
        read_only_fields = ["created_at"]

    def get_acked(self, obj):
        """当前登录用户是否已读确认"""
        request = self.context.get("request")
        user = request.user if request else None
        if not user or not user.is_authenticated:
            return False
        return RegulationAck.objects.filter(regulation=obj, user=user).exists()


class RegulationAckSerializer(serializers.ModelSerializer):
    """制度已读确认记录"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    regulation_title = serializers.CharField(source="regulation.title", read_only=True)

    class Meta:
        model = RegulationAck
        fields = ["id", "regulation", "regulation_title", "user", "user_name", "read_at"]
        read_only_fields = ["read_at"]


class KnowledgeCategorySerializer(serializers.ModelSerializer):
    """知识分类（含一级子分类）"""
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeCategory
        fields = ["id", "name", "parent", "parent_name", "sort", "children"]

    def get_children(self, obj):
        """返回未删除的子分类"""
        qs = obj.children.filter(is_deleted=False)
        return KnowledgeCategorySerializer(qs, many=True, context=self.context).data


class KnowledgeArticleSerializer(serializers.ModelSerializer):
    """知识库文章"""
    category_name = serializers.CharField(source="get_category_display", read_only=True)
    level_name = serializers.CharField(source="get_level_display", read_only=True)
    knowledge_category_name = serializers.CharField(source="knowledge_category.name", read_only=True)
    finished = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeArticle
        fields = ["id", "title", "category", "category_name", "knowledge_category",
                  "knowledge_category_name", "level", "level_name", "summary", "content",
                  "video_url", "attachment", "tags", "is_published", "is_required",
                  "sort", "view_count", "finished", "created_at"]
        read_only_fields = ["view_count", "created_at"]

    def get_finished(self, obj):
        """当前登录用户是否已完成学习"""
        request = self.context.get("request")
        user = request.user if request else None
        if not user or not user.is_authenticated:
            return False
        return LearningRecord.objects.filter(article=obj, user=user, finished=True).exists()


class LearningRecordSerializer(serializers.ModelSerializer):
    """学习进度"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    article_title = serializers.CharField(source="article.title", read_only=True)

    class Meta:
        model = LearningRecord
        fields = ["id", "user", "user_name", "article", "article_title",
                  "finished", "duration", "last_at"]
        read_only_fields = ["last_at"]


class QuestionBankSerializer(serializers.ModelSerializer):
    """题库"""
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = QuestionBank
        fields = ["id", "name", "description", "question_count", "created_at"]

    def get_question_count(self, obj):
        return obj.questions.filter(is_deleted=False).count()


class QuestionListSerializer(serializers.ModelSerializer):
    """题目列表序列化器（不含正确答案，学生端使用）"""
    qtype_name = serializers.CharField(source="get_qtype_display", read_only=True)
    bank_name = serializers.CharField(source="bank.name", read_only=True)

    class Meta:
        model = Question
        fields = ["id", "bank", "bank_name", "qtype", "qtype_name", "stem",
                  "options", "score", "level"]


class QuestionSerializer(serializers.ModelSerializer):
    """题目详情序列化器（含正确答案，管理端使用）"""
    qtype_name = serializers.CharField(source="get_qtype_display", read_only=True)
    bank_name = serializers.CharField(source="bank.name", read_only=True)

    class Meta:
        model = Question
        fields = ["id", "bank", "bank_name", "qtype", "qtype_name", "stem",
                  "options", "answer", "analysis", "score", "level", "created_at"]


class ExamSerializer(serializers.ModelSerializer):
    """考试"""
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    bank_name = serializers.CharField(source="bank.name", read_only=True)

    class Meta:
        model = Exam
        fields = ["id", "title", "description", "bank", "bank_name", "question_count",
                  "total_score", "pass_score", "duration", "status", "status_name",
                  "start_at", "end_at", "allow_retake", "max_attempts", "created_at"]


class ExamRecordSerializer(serializers.ModelSerializer):
    """考试记录"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    exam_title = serializers.CharField(source="exam.title", read_only=True)

    class Meta:
        model = ExamRecord
        fields = ["id", "exam", "exam_title", "user", "user_name", "score", "passed",
                  "answers", "started_at", "submitted_at", "attempt"]
        read_only_fields = ["started_at"]


class OnboardingProfileSerializer(serializers.ModelSerializer):
    """入职资料"""
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    education_name = serializers.CharField(source="get_education_display", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    review_by_name = serializers.CharField(source="review_by.display_name", read_only=True)

    class Meta:
        model = OnboardingProfile
        fields = ["id", "name", "phone", "id_card_no", "gender", "birth_date",
                  "education", "education_name", "school", "address",
                  "emergency_contact", "emergency_phone", "bank_card_no",
                  "department", "department_name", "position", "entry_date",
                  "id_card_front", "id_card_back", "diploma", "bank_card_img",
                  "photo", "resume", "other_files",
                  "status", "status_name", "review_by", "review_by_name",
                  "review_at", "review_remark", "bound_user", "created_at"]
        read_only_fields = ["status", "review_by", "review_at", "review_remark",
                            "bound_user", "created_at"]


class OnboardingTaskSerializer(serializers.ModelSerializer):
    """入职任务"""
    task_type_name = serializers.CharField(source="get_task_type_display", read_only=True)
    regulation_title = serializers.CharField(source="regulation.title", read_only=True)
    article_title = serializers.CharField(source="article.title", read_only=True)
    exam_title = serializers.CharField(source="exam.title", read_only=True)

    class Meta:
        model = OnboardingTask
        fields = ["id", "title", "task_type", "task_type_name", "description",
                  "regulation", "regulation_title", "article", "article_title",
                  "exam", "exam_title", "due_days", "required", "sort"]


class OnboardingTaskRecordSerializer(serializers.ModelSerializer):
    """入职任务完成记录"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    task_title = serializers.CharField(source="task.title", read_only=True)

    class Meta:
        model = OnboardingTaskRecord
        fields = ["id", "user", "user_name", "task", "task_title", "finished", "finished_at"]
        read_only_fields = ["finished_at"]
