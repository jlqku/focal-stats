from kivy.core.text import LabelBase
LabelBase.register(name='Roboto', fn_regular='NotoSansCJK-Regular.ttc')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from threading import Thread
from collections import Counter
import os

try:
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    IS_ANDROID = True
except ImportError:
    IS_ANDROID = False

class FocalStatsApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        self.btn = Button(
            text='开始分析相册',
            font_size='20sp',
            size_hint=(1, 0.1),
            background_color=(0.2, 0.6, 0.8, 1)
        )
        self.btn.bind(on_press=self.start_analysis)

        self.status = Label(
            text='点击按钮开始分析照片焦段',
            font_size='16sp',
            size_hint=(1, 0.05)
        )

        self.scroll = ScrollView(size_hint=(1, 0.85))
        self.result = TextInput(
            readonly=True,
            multiline=True,
            font_size='14sp',
            background_color=(0.1, 0.1, 0.15, 1),
            foreground_color=(1, 1, 1, 1)
        )
        self.scroll.add_widget(self.result)

        self.layout.add_widget(self.btn)
        self.layout.add_widget(self.status)
        self.layout.add_widget(self.scroll)

        if IS_ANDROID:
            Clock.schedule_once(self.request_perm, 0)

        return self.layout

    def request_perm(self, dt):
        request_permissions([
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE
        ])

    def start_analysis(self, instance):
        self.btn.disabled = True
        self.result.text = ''
        Thread(target=self.analyze).start()

    def analyze(self):
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            if IS_ANDROID:
                base = primary_external_storage_path()
            else:
                base = os.path.expanduser('~')

            paths = [
                os.path.join(base, 'DCIM', 'Camera'),
                os.path.join(base, 'Pictures'),
                os.path.join(base, 'DCIM'),
            ]

            files = []
            for p in paths:
                if os.path.exists(p):
                    for root, _, fnames in os.walk(p):
                        for f in fnames:
                            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.raf', '.dng')):
                                files.append(os.path.join(root, f))

            self.update_status(f'找到 {len(files)} 张照片，分析中...')

            focals = []
            for i, f in enumerate(files):
                fl = self.get_focal(f)
                if fl:
                    focals.append(fl)
                if i % 50 == 0:
                    self.update_status(f'已处理 {i+1}/{len(files)}...')

            if not focals:
                self.update_result('未找到带焦段信息的照片')
                return

            result = self.format_result(focals, len(files))
            self.update_result(result)

        except Exception as e:
            self.update_result(f'出错: {str(e)}')
        finally:
            self.btn.disabled = False

    def get_focal(self, path):
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            img = Image.open(path)
            exif = img._getexif()
            if not exif:
                return None
            for tag_id, value in exif.items():
                if TAGS.get(tag_id) == 'FocalLength':
                    if isinstance(value, tuple):
                        return float(value[0]) / float(value[1])
                    return float(value)
        except:
            pass
        return None

    def format_result(self, focals, total_files):
        lines = []
        lines.append(f'📊 共扫描 {total_files} 张，有效 {len(focals)} 张\n')
        lines.append(f'最短: {min(focals):.0f}mm | 最长: {max(focals):.0f}mm | 平均: {sum(focals)/len(focals):.0f}mm\n')
        lines.append('━' * 40)

        bins = [
            ('超广 <16mm', lambda x: x < 16),
            ('广角 16-35mm', lambda x: 16 <= x <= 35),
            ('标准 35-70mm', lambda x: 35 < x <= 70),
            ('中长 70-135mm', lambda x: 70 < x <= 135),
            ('长焦 >135mm', lambda x: x > 135),
        ]

        total = len(focals)
        for label, check in bins:
            count = sum(1 for f in focals if check(f))
            pct = count / total * 100
            bar = '█' * int(pct / 2.5)
            lines.append(f'{label:14s}: {count:4d}张 ({pct:5.1f}%) {bar}')

        lines.append('\n' + '━' * 40)
        lines.append('📷 最常用焦距 Top 10:')
        for fl, c in Counter(focals).most_common(10):
            lines.append(f'  {fl:6.0f}mm: {c}张')

        return '\n'.join(lines)

    def update_status(self, text):
        Clock.schedule_once(lambda dt: setattr(self.status, 'text', text), 0)

    def update_result(self, text):
        Clock.schedule_once(lambda dt: setattr(self.result, 'text', text), 0)

if __name__ == '__main__':
    FocalStatsApp().run()