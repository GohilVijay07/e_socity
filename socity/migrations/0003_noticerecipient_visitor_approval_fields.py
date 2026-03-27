from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('socity', '0002_building_complaintupdate_staff_task_visitorapproval_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='visitor',
            name='approval_note',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='visitor',
            name='approval_status',
            field=models.CharField(
                choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')],
                default='PENDING',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='NoticeRecipient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('notice', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='recipients', to='socity.notice')),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='notice_recipients', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('notice', 'user')},
            },
        ),
    ]
