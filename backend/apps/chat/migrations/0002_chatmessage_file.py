from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='message_type',
            field=models.CharField(
                choices=[('text', 'Текст'), ('image', 'Изображение'), ('file', 'Файл')],
                default='text',
                max_length=10,
                verbose_name='Тип сообщения'
            ),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='chat/files/%Y/%m/', verbose_name='Файл'),
        ),
        migrations.AlterField(
            model_name='chatmessage',
            name='content',
            field=models.TextField(blank=True, verbose_name='Содержание'),
        ),
    ]
