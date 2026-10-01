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
                  "date_joined", "last_login", "is_superuser"]
        read_only_fields = ["date_joined", "last_login", "is_superuser"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, default="123456")

    class Meta:
        model = User
        fields = ["id", "username", "password", "first_name", "phone", "email", "employee_no",
                  "department", "team", "position", "role", "status", "entry_date",
                  "month_target", "base_salary"]

    def create(self, validated_data):
        pwd = validated_data.pop("password", "123456")
        user = User(**validated_data)
        user.set_password(pwd)
        user.save()
        return user

    def update(self, instance, validated_data):
        pwd = validated_data.pop("password", None)
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
