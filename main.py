from kivy.core.text import LabelBase
LabelBase.register(name='Roboto', fn_regular='NotoSansCJK-Regular.ttc')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
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

        btn_box = BoxLayout(size_hint=(1, 0.1), spacing=10)

        self.btn_auto = Button(
            text='自动扫描',
            font_size='18sp',
            background_color=(0.2, 0.6, 0.8, 1)
        )
        self.btn_auto.bind(on_press=self.start_analysis)

        self.btn_manual = Button(
            text='手动选择',
            font_size='18sp',
            background_color=(0.2, 0.7, 0.5, 1)
        )
        self.btn_manual.bind(on_press=self.show_file_chooser)

        btn_box.add_widget(self.btn_auto)
        btn_box.add_widget(self.btn_manual)

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

        self.layout.add_widget(btn_box)
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

    def show_file_chooser(self, instance):
        content = BoxLayout(orientation='vertical')

        if IS_ANDROID:
            default_path = primary_external_storage_path()
        else:
            default_path = os.path.expanduser('~')

        filechooser = FileChooserListView(
            path=default_path,
            dirselect=True,
            show_hidden=False
        )
        content.add_widget(filechooser)

        path_label = Label(
            text=default_path,
            size_hint=(1, 0.05),
            font_size='12sp'
        )
        content.add_widget(path_label)

        btn_box = BoxLayout(size_hint=(1, 0.08), spacing=10)

        def on_select(instance):
            if filechooser.selection:
                selected = filechooser.selection[0]
                if os.path.isdir(selected):
                    popup.dismiss()
                    self.start_analysis_manual(selected)
                else:
                    path_label.text = '请选择一个文件夹，不是文件'
            else:
                path_label.text = '请先选择一个文件夹'

        select_btn = Button(text='选择此文件夹')
        select_btn.bind(on_press=on_select)

        cancel_btn = Button(text='取消')
        cancel_btn.bind(on_press=lambda x: popup.dismiss())

        btn_box.add_widget(select_btn)
        btn_box.add_widget(cancel_btn)
        content.add_widget(btn_box)

        popup = Popup(
            title='选择相册文件夹',
            content=content,
            size_hint=(0.95, 0.95),
            auto_dismiss=False
        )
        popup.open()

    def start_analysis(self, instance):
        self.btn_auto.disabled = True
        self.btn_manual.disabled = True
        self.result.text = ''
        Thread(target=self.analyze_auto).start()

    def start_analysis_manual(self, folder):
        self.btn_auto.disabled = True
        self.btn_manual.disabled = True
        self.result.text = ''
        Thread(target=lambda: self.analyze(folder)).start()

    def analyze_auto(self):
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

        self.analyze_with_files(files)

    def analyze(self, folder=None):
        try:
            files = []
            if folder and os.path.exists(folder):
                for root, _, fnames in os.walk(folder):
                    for f in fnames:
                        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.raf', '.dng')):
                            files.append(os.path.join(root, f))
            else:
                self.update_result('文件夹路径无效')
                return

            self.analyze_with_files(files)

        except Exception as e:
            self.update_result(f'出错: {str(e)}')
        finally:
            self.update_ui_enabled()

    def analyze_with_files(self, files):
        try:
            self.update_status(f'找到 {len(files)} 张照片，分析中...')

            focals = []
            for i, f in enumerate(files):
                fl = self.get_focal(f)
                if fl:
                    focals.append(fl)
                if i % 50 == 0:
                    self.update_status(f'已处理 {i+1}/{len(files)}...')

            if not focals:
                self.update_result('未找到带焦段信息的照片（可能是 HEIC 格式或 EXIF 被清理）')
                return

            result = self.format_result(focals, len(files))
            self.update_result(result)

        except Exception as e:
            self.update_result(f'出错: {str(e)}')
        finally:
            self.update_ui_enabled()

    def update_ui_enabled(self):
        Clock.schedule_once(lambda dt: setattr(self.btn_auto, 'disabled', False), 0)
        Clock.schedule_once(lambda dt: setattr(self.btn_manual, 'disabled', False), 0)

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
        lines.append(f'共扫描 {total_files} 张，有效 {len(focals)} 张\n')
        lines.append(f'最短: {min(focals):.0f}mm | 最长: {max(focals):.0f}mm | 平均: {sum(focals)/len(focals):.0f}mm\n')
        lines.append('=' * 40)

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

        lines.append('\n' + '=' * 40)
        lines.append('最常用焦距 Top 10:')
        for fl, c in Counter(focals).most_common(10):
            lines.append(f'  {fl:6.0f}mm: {c}张')

        return '\n'.join(lines)

    def update_status(self, text):
        Clock.schedule_once(lambda dt: setattr(self.status, 'text', text), 0)

    def update_result(self, text):
        Clock.schedule_once(lambda dt: setattr(self.result, 'text', text), 0)

if __name__ == '__main__':
    FocalStatsApp().run()
