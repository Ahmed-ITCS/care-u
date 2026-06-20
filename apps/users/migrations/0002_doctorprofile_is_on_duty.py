from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctorprofile',
            name='is_on_duty',
            field=models.BooleanField(
                default=True,
                help_text='When off duty, doctor is hidden from appointment booking.',
            ),
        ),
    ]
