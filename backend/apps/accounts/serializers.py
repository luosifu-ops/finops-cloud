from rest_framework import serializers
from .models import User, Department, Team, Position, CompanyProfile


class DepartmentSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ["id", "name", "code", "leader", "leader_name", "parent", "description", "order", "member_count"]
        read_only_fields = ["leader_name", "member_count"]

    leader_name = serializers.CharField(source="leader.display_name", read_only=True)

    def get_member_count(self, obj):
        return obj.members.filter(status__in=["PROBATION", "REGULAR", "INTERN"]).count()


class TeamSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    leader_name = serializers.CharField(source="leader.display_name", read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id", "name", "department", "department_name", "leader", "leader_name",
                  "month_target", "member_count"]

    def get_member_count(self, obj):
        return obj.members.filter(status__in=["PROBATION", "REGULAR", "INTERN"]).count()


class PositionSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Position
        fields = ["id", "name", "department", "department_name", "description"]


class UserListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True)
    job_level_name = serializers.CharField(source="job_level.name", read_only=True)
    role_name = serializers.CharField(source="get_role_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "display_name", "employee_no", "phone", "avatar",
                  "department", "department_name", "team", "team_name",
                  "position", "position_name", "job_level", "job_level_name",
                  "role", "role_name", "status", "status_name", "entry_date",
                  "probation_end", "month_target", "base_salary"]


class UserDetailSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True)
    job_level_name = serializers.CharField(source="job_level.name", read_only=True)
    role_name = serializers.CharField(source="get_role_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "display_name", "email",
                  "employee_no", "phone", "avatar", "department", "department_name",
                  "team", "team_name", "position", "position_name", "job_level", "job_level_name",
                  "role", "role_name", "status", "status_name", "entry_date", "regular_date",
                  "probation_end", "leave_date", "id_card_no", "bank_card_no", "address",
                  "emergency_contact", "emergency_phone", "month_target", "base_salary",
                  "date_joined", "last_login", "is_superuser", "can_assign_leads"]
        read_only_fields = ["date_joined", "last_login", "is_superuser"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, default="123456")
    # 用户名允许留空：留空时自动用手机号兜底（本系统以手机号作登录账号）。
    # 显式声明后 DRF 不再自动挂 UniqueValidator，改由 validate_username 自己校验唯一，
    # 既能支持"留空"，也不会出现重复用户名导致的 500。
    username = serializers.CharField(required=False, allow_blank=True, max_length=150)

    class Meta:
        model = User
        fields = ["id", "username", "password", "first_name", "phone", "email", "employee_no",
                  "department", "team", "position", "role", "status", "entry_date",
                  "probation_end", "regular_date", "month_target", "base_salary"]

    def validate_username(self, value):
        value = (value or "").strip()
        if not value:
            return value
        qs = User.objects.filter(username=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("该用户名已被占用，请换一个")
        return value

    def create(self, validated_data):
        pwd = validated_data.pop("password", "123456")
        # 工号留空时由 User.save() 自动生成（EMP0001 起），前端无需填
        if not validated_data.get("employee_no"):
            validated_data.pop("employee_no", None)
        # 用户名为空时用手机号兜底（本系统一直以手机号作为登录账号）
        if not (validated_data.get("username") or "").strip():
            validated_data["username"] = (validated_data.get("phone") or "").strip()
        if not validated_data.get("username"):
            raise serializers.ValidationError({"username": "用户名与手机号至少填写一项"})
        user = User(**validated_data)
        user.set_password(pwd)
        user.save()
        return user

    def update(self, instance, validated_data):
        # 隔离墙（2026-10-28）：非管理层仅能修改本人资料，且组织/权限/薪酬字段一律忽略
        request = self.context.get("request")
        if request is not None:
            u = request.user
            is_manager = bool(u and u.is_authenticated and
                              (u.is_superuser or u.role in ("BOSS", "HR", "MANAGER")))
            if not is_manager:
                if instance.pk != u.pk:
                    raise serializers.ValidationError("无权修改他人资料")
                for f in ("role", "department", "team", "position", "status",
                          "entry_date", "probation_end", "regular_date",
                          "base_salary", "month_target", "employee_no", "username",
                          "is_active", "is_staff", "is_superuser"):
                    validated_data.pop(f, None)
        pwd = validated_data.pop("password", None)
        # 工号被清空时保留原编号（由 User.save() 兜底沿用），不因编辑而换号
        if "employee_no" in validated_data and not validated_data.get("employee_no"):
            validated_data.pop("employee_no")
        # 用户名被清空时保留原账号，避免把登录名改成空串
        if "username" in validated_data and not (validated_data.get("username") or "").strip():
            validated_data.pop("username")
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if pwd:
            instance.set_password(pwd)
        instance.save()
        return instance


class CompanyProfileSerializer(serializers.ModelSerializer):
    """公司简介与联系方式（单例）"""
    class Meta:
        model = CompanyProfile
        fields = [
            "id", "name", "short_name", "credit_code", "legal_person",
            "registered_capital", "established_date", "business_scope", "intro", "culture",
            "address", "phone", "email", "wechat", "website",
            "qcc_screenshot", "logo", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
