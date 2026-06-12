from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TenantUserIndex',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(db_index=True, max_length=150)),
                ('email', models.EmailField(blank=True, db_index=True, max_length=254)),
                ('is_active', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('hospital', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_index', to='tenants.hospital')),
            ],
            options={
                'verbose_name': 'Tenant User Index',
                'unique_together': {('hospital', 'username')},
                'indexes': [
                    models.Index(fields=['email'], name='tenants_ten_email_idx'),
                    models.Index(fields=['username'], name='tenants_ten_usernam_idx'),
                ],
            },
        ),
    ]
