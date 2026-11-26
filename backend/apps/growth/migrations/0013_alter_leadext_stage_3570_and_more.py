# 2026-11-26 Boss 指示：已承接线索池「其他需求」增加「暂时无需求」阶段（原来没有，新增）
#
# 说明：仅扩展 stage_3570 的可选项（choices），不改表结构、不改任何存量数据；
#       「无需求(SN)」原有选项保留。手工编写并挂在两个叶子迁移之后，
#       避免 makemigrations 因双叶子节点额外生成 merge 迁移。

from django.db import migrations, models


STAGE_3570 = [
    ('S3', '3阶段'), ('S5', '5阶段'), ('S7', '7阶段'), ('S0', '0成交'),
    ('SN', '无需求'), ('ST', '暂时无需求'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('growth', '0011_alter_leadpool_status'),
        ('growth', '0010_alter_leadext_stage_3570_alter_leadpool_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leadext',
            name='stage_3570',
            field=models.CharField(blank=True, choices=STAGE_3570, default='',
                                   help_text='人工手动标记，不强制自动算法；S0=0成交阶段',
                                   max_length=5, verbose_name='3570阶段'),
        ),
        migrations.AlterField(
            model_name='leadstagelog',
            name='new_stage',
            field=models.CharField(blank=True, choices=STAGE_3570, default='',
                                   max_length=5, verbose_name='新阶段'),
        ),
    ]
