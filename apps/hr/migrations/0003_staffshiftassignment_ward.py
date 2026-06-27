import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinical', '0002_initial'),
        ('hr', '0002_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='staffshiftassignment',
            options={'ordering': ['-date', 'shift__start_time']},
        ),
        migrations.AddField(
            model_name='staffshiftassignment',
            name='ward',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='shift_assignments',
                to='clinical.ward',
            ),
        ),
        migrations.AlterField(
            model_name='staffshiftassignment',
            name='date',
            field=models.DateField(db_index=True),
        ),
        migrations.AlterField(
            model_name='staffshiftassignment',
            name='shift',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assignments',
                to='hr.shift',
            ),
        ),
    ]
