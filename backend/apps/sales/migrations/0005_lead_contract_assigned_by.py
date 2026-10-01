# Generated manually for 阶段三：主管可编辑权限扩展 —— 记录线索/合同的分配人
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0004_contract_payment_screenshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='assigned_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='assigned_leads',
                to='accounts.user',
                verbose_name='分配人',
            ),
        ),
        migrations.AddField(
            model_name='contract',
            name='assigned_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='assigned_contracts',
                to='accounts.user',
                verbose_name='分配人',
            ),
        ),
    ]
