from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets

router = DefaultRouter()
router.register("tax-types", viewsets.TaxTypeViewSet, basename="tax-type")
router.register("clients", viewsets.AccountingClientViewSet, basename="accounting-client")
router.register("monthly-tasks", viewsets.MonthlyTaskViewSet, basename="monthly-task")
router.register("task-steps", viewsets.TaskStepViewSet, basename="task-step")
router.register("vouchers", viewsets.VoucherViewSet, basename="voucher")
router.register("invoices", viewsets.InvoiceViewSet, basename="invoice")
router.register("bank-statements", viewsets.BankStatementViewSet, basename="bank-statement")
router.register("tax-declarations", viewsets.TaxDeclarationViewSet, basename="tax-declaration")
router.register("social-insurances", viewsets.SocialInsuranceViewSet, basename="social-insurance")
router.register("annual-reports", viewsets.AnnualReportViewSet, basename="annual-report")
router.register("business-items", viewsets.BusinessItemViewSet, basename="business-item")
router.register("client-documents", viewsets.ClientDocumentViewSet, basename="client-document")
router.register("handovers", viewsets.HandoverRecordViewSet, basename="handover-record")
router.register("book-sets", viewsets.BookSetViewSet, basename="book-set")
router.register("client-payments", viewsets.ClientPaymentViewSet, basename="client-payment")

urlpatterns = [
    path("", include(router.urls)),
    path("reminders/", viewsets.ReminderCenterApiView.as_view(), name="accounting-reminders"),
]
