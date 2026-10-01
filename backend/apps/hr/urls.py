from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets

router = DefaultRouter()
router.register("attendance-rules", viewsets.AttendanceRuleViewSet, basename="attendance-rule")
router.register("attendances", viewsets.AttendanceViewSet, basename="attendance")
router.register("attendance-stats", viewsets.AttendanceStatViewSet, basename="attendance-stat")
router.register("leaves", viewsets.LeaveApplicationViewSet, basename="leave")
router.register("overtimes", viewsets.OvertimeApplicationViewSet, basename="overtime")
router.register("travels", viewsets.TravelApplicationViewSet, basename="travel")
router.register("expenses", viewsets.ExpenseApplicationViewSet, basename="expense")
router.register("approvals", viewsets.ApprovalViewSet, basename="approval")
router.register("approval-steps", viewsets.ApprovalStepViewSet, basename="approval-step")
router.register("salaries", viewsets.SalaryViewSet, basename="hr-salary")
# 钉钉缺失功能补全（2026-09-12 增量）
router.register("job-levels", viewsets.JobLevelViewSet, basename="job-level")
router.register("external-contacts", viewsets.ExternalContactViewSet, basename="external-contact")
router.register("user-attachments", viewsets.UserAttachmentViewSet, basename="user-attachment")
router.register("change-logs", viewsets.EmployeeChangeLogViewSet, basename="change-log")
router.register("labor-contracts", viewsets.LaborContractViewSet, basename="labor-contract")
router.register("regularizations", viewsets.RegularizationApplicationViewSet, basename="regularization")
router.register("transfers", viewsets.TransferApplicationViewSet, basename="transfer")
router.register("resignations", viewsets.ResignApplicationViewSet, basename="resignation")
router.register("attendance-groups", viewsets.AttendanceGroupViewSet, basename="attendance-group")
router.register("shifts", viewsets.ShiftScheduleViewSet, basename="shift")
router.register("leave-balances", viewsets.LeaveBalanceViewSet, basename="leave-balance")
router.register("purchases", viewsets.PurchaseApplicationViewSet, basename="purchase")
router.register("seals", viewsets.SealApplicationViewSet, basename="seal")
router.register("performance-plans", viewsets.PerformancePlanViewSet, basename="performance-plan")
router.register("performance-reviews", viewsets.PerformanceReviewViewSet, basename="performance-review")
router.register("addressbook-visibility", viewsets.AddressBookVisibilityViewSet, basename="addressbook-visibility")
router.register("role-presets", viewsets.RolePresetViewSet, basename="role-preset")

urlpatterns = [
    # 人事业绩统计（个人 / 部门周期）
    path("performance/stat/", viewsets.performance_stat, name="hr-performance-stat"),
    path("", include(router.urls)),
]
