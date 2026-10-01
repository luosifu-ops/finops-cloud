# Generated manually for 阶段二/三：外勤主管派单支持手动录入姓名 + 记录派单人
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('growth', '0006_fieldtask_business_type_alter_fieldtasknode_node'),
    ]

    operations = [
        migrations.AddField(
            model_name='fieldtask',
            name='assignee_name',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=100,
                verbose_name='外勤人员名称',
            ),
        ),
        migrations.AddField(
            model_name='fieldtask',
            name='assigned_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='assigned_field_tasks',
                to='accounts.user',
                verbose_name='派单人',
            ),
        ),
    ]
