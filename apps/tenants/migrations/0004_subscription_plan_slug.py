from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0003_rename_tenants_ten_email_idx_tenants_ten_email_a591ae_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriptionplan',
            name='name',
            field=models.SlugField(
                help_text='Internal slug, e.g. premium or acme-hospital',
                max_length=50,
                unique=True,
            ),
        ),
    ]
