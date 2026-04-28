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
from datetime import datetime

try:
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    IS_ANDROID = True
except ImportError:
    IS_ANDROID = False

class FocalStatsApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=15, spacing=8)

        btn_box = BoxLayout(size_hint=(1, 0.1), spacing=10)
        self.btn_auto = Button(
            text='\u81ea\u52a8\u626b\u63cf',
            font_size='18sp',
            background_color=(0.2, 0.6, 0.8, 1)
        )
        self.btn_auto.bind(on_press=self.start_analysis)
        self.btn_manual = Button(
            text='\u624b\u52a8\u9009\u62e9',
            font_size='18sp',
            background_color=(0.2, 0.7, 0.5, 1)
        )
        self.btn_manual.bind(on_press=self.show_file_chooser)
        btn_box.add_widget(self.btn_auto)
        btn_box.add_widget(self.btn_manual)

        # 日期过滤栏
        filter_box = BoxLayout(size_hint=(1, 0.08), spacing=5)
        filter_box.add_widget(Label(text='\u65e5\u671f\u4ece:', size_hint=(0.18, 1), font_size='13sp'))
        self.date_from = TextInput(
            hint_text='2024-01-01',
            size_hint=(0.28, 1),
            multiline=False,
            font_size='13sp',
            padding_y=(8, 8)
        )
        filter_box.add_widget(self.date_from)
        filter_box.add_widget(Label(text='\u5230:', size_hint=(0.1, 1), font_size='13sp'))
        self.date_to = TextInput(
            hint_text='2025-12-31',
            size_hint=(0.28, 1),
            multiline=False,
            font_size='13sp',
            padding_y=(8, 8)
        )
        filter_box.add_widget(self.date_to)
        self.layout.add_widget(btn_box)
        self.layout.add_widget(filter_box)

        self.status = Label(
            text='\u70b9\u51fb\u6309\u94ae\u5f00\u59cb\u5206\u6790\u7167\u7247\u7126\u6bb5\uff0c\u53ef\u9009\u586b\u65e5\u671f\u8fc7\u6ee4',
            font_size='14sp',
            size_hint=(1, 0.06)
        )

        self.scroll = ScrollView(size_hint=(1, 0.76))
        self.result = TextInput(
            readonly=True,
            multiline=True,
            font_size='13sp',
            background_color=(0.1, 0.1, 0.15, 1),
            foreground_color=(1, 1, 1, 1)
        )
        self.scroll.add_widget(self.result)

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
                    path_label.text = '\u8bf7\u9009\u62e9\u6587\u4ef6\u5939\uff0c\u4e0d\u662f\u6587\u4ef6'
            else:
                path_label.text = '\u8bf7\u5148\u9009\u62e9\u6587\u4ef6\u5939'

        select_btn = Button(text='\u9009\u62e9\u6b64\u6587\u4ef6\u5939')
        select_btn.bind(on_press=on_select)
        cancel_btn = Button(text='\u53d6\u6d88')
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        btn_box.add_widget(select_btn)
        btn_box.add_widget(cancel_btn)
        content.add_widget(btn_box)
        popup = Popup(
            title='\u9009\u62e9\u76f8\u518c\u6587\u4ef6\u5939',
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

    def parse_date_range(self):
        df = self.date_from.text.strip()
        dt = self.date_to.text.strip()
        d_from = None
        d_to = None
        if df:
            try:
                d_from = datetime.strptime(df, '%Y-%m-%d')
            except:
                pass
        if dt:
            try:
                d_to = datetime.strptime(dt, '%Y-%m-%d')
                d_to = d_to.replace(hour=23, minute=59, second=59)
            except:
                pass
        return d_from, d_to

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
        self.analyze_with_files(files, auto_paths=paths)

    def analyze(self, folder=None):
        try:
            debug_lines = []
            debug_lines.append(f'\u76ee\u6807\u6587\u4ef6\u5939: {folder}')
            debug_lines.append(f'\u8def\u5f84\u662f\u5426\u5b58\u5728: {os.path.exists(folder) if folder else False}')
            files = []
            last_dir = ''
            if folder and os.path.exists(folder):
                walked_dirs = 0
                for root, _, fnames in os.walk(folder):
                    walked_dirs += 1
                    last_dir = root
                    if walked_dirs % 10 == 0:
                        self.update_status(f'\u6b63\u5728\u626b\u63cf: {root} ({walked_dirs} \u4e2a\u76ee\u5f55)...')
                    for f in fnames:
                        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.raf', '.dng')):
                            files.append(os.path.join(root, f))
                debug_lines.append(f'\u6700\u540e\u626b\u63cf\u7684\u76ee\u5f55: {last_dir}')
                debug_lines.append(f'\u904d\u5386\u4e86 {walked_dirs} \u4e2a\u5b50\u76ee\u5f55')
                debug_lines.append(f'\u7b5b\u9009\u540e\u7167\u7247: {len(files)} \u5f20')
            else:
                debug_lines.append('\u6587\u4ef6\u5939\u8def\u5f84\u65e0\u6548\uff0c\u5206\u6790\u7ed3\u675f')
                self.update_result('\n'.join(debug_lines))
                return
            self.analyze_with_files(files, debug_prefix='\n'.join(debug_lines) + '\n')
        except Exception as e:
            self.update_result(f'\u51fa\u9519: {str(e)}')
        finally:
            self.update_ui_enabled()

    def analyze_with_files(self, files, debug_prefix='', auto_paths=None):
        try:
            self.update_status(f'\u627e\u5230 {len(files)} \u5f20\u7167\u7247\uff0c\u5206\u6790\u4e2d...')
            date_from, date_to = self.parse_date_range()
            if date_from or date_to:
                self.update_status(f'\u542f\u7528\u65e5\u671f\u8fc7\u6ee4: {date_from.date() if date_from else "\u65e0\u9650"} ~ {date_to.date() if date_to else "\u65e0\u9650"}')

            focal_data = []  # [(focal, filename, dt), ...]
            for i, f in enumerate(files):
                info = self.get_exif_info(f)
                if info:
                    focal, dt = info
                    focal_data.append((focal, f, dt))
                if i % 50 == 0:
                    self.update_status(f'\u5df2\u5904\u7406 {i+1}/{len(files)}...')

            # 日期过滤
            filtered = []
            for focal, fpath, dt in focal_data:
                if dt is None:
                    continue
                if date_from and dt < date_from:
                    continue
                if date_to and dt > date_to:
                    continue
                filtered.append((focal, fpath))

            lines = []
            if debug_prefix:
                lines.append(debug_prefix)
            if auto_paths:
                lines.append(f'\u81ea\u52a8\u626b\u63cf\u8def\u5f84: {auto_paths}')
                lines.append('')
            if date_from or date_to:
                lines.append(f'\u65e5\u671f\u8fc7\u6ee4: {date_from.date() if date_from else "\u4e0d\u9650"} ~ {date_to.date() if date_to else "\u4e0d\u9650"}')
                lines.append('')

            if not filtered:
                lines.append('\u672a\u627e\u5230\u7b26\u5408\u6761\u4ef6\u7684\u7167\u7247')
                lines.append('\u53ef\u80fd\u539f\u56e0: \u65e5\u671f\u8fc7\u6ee4\u8303\u56f4\u592a\u7a84 / EXIF\u65e5\u671f\u4e22\u5931 / \u6ca1\u6709\u5b58\u50a8\u6743\u9650')
                self.update_result('\n'.join(lines))
                return

            result = self.format_result(filtered, len(files))
            lines.append(result)
            self.update_result('\n'.join(lines))
        except Exception as e:
            self.update_result(f'\u51fa\u9519: {str(e)}')
        finally:
            self.update_ui_enabled()

    def update_ui_enabled(self):
        Clock.schedule_once(lambda dt: setattr(self.btn_auto, 'disabled', False), 0)
        Clock.schedule_once(lambda dt: setattr(self.btn_manual, 'disabled', False), 0)

    def get_exif_info(self, path):
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            img = Image.open(path)
            exif = img._getexif()
            if not exif:
                return None
            focal = None
            dt = None
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id)
                if tag == 'FocalLength':
                    if isinstance(value, tuple):
                        focal = float(value[0]) / float(value[1])
                    else:
                        focal = float(value)
                elif tag in ('DateTimeOriginal', 'DateTime'):
                    try:
                        dt = datetime.strptime(str(value), '%Y:%m:%d %H:%M:%S')
                    except:
                        pass
            if focal is not None:
                return (focal, dt)
        except Exception:
            pass
        return None

    def format_result(self, filtered, total_files):
        # filtered: [(focal, filepath), ...]
        focals = [x[0] for x in filtered]
        focal_files = {}
        for focal, fpath in filtered:
            focal_files.setdefault(focal, []).append(fpath)

        lines = []
        lines.append(f'\u5171\u626b\u63cf {total_files} \u5f20\uff0c\u6709\u6548 {len(focals)} \u5f20')
        lines.append(f'\u6700\u77ed: {min(focals):.0f}mm | \u6700\u957f: {max(focals):.0f}mm | \u5e73\u5747: {sum(focals)/len(focals):.0f}mm')
        lines.append('=' * 40)

        bins = [
            ('\u8d85\u5e7f <16mm', lambda x: x < 16),
            ('\u5e7f\u89d2 16-35mm', lambda x: 16 <= x <= 35),
            ('\u6807\u51c6 35-70mm', lambda x: 35 < x <= 70),
            ('\u4e2d\u957f 70-135mm', lambda x: 70 < x <= 135),
            ('\u957f\u7126 >135mm', lambda x: x > 135),
        ]
        total = len(focals)
        for label, check in bins:
            count = sum(1 for f in focals if check(f))
            pct = count / total * 100
            bar = '\u2588' * int(pct / 2.5)
            lines.append(f'{label:14s}: {count:4d}\u5f20 ({pct:5.1f}%) {bar}')

        lines.append('')
        lines.append('=' * 40)
        lines.append('\u6700\u5e38\u7528\u7126\u8ddd Top 10:')
        for fl, c in Counter(focals).most_common(10):
            lines.append(f'  {fl:6.0f}mm: {c}\u5f20')

        lines.append('')
        lines.append('=' * 40)
        lines.append('\u5404\u7126\u6bb5\u7167\u7247\u660e\u7ec6\uff08\u6bcf\u4e2a\u7126\u6bb5\u663e\u793a\u524d5\u5f20\uff09:')
        lines.append('')
        for fl in sorted(focal_files.keys(), reverse=True):
            files = focal_files[fl]
            lines.append(f'--- {fl:.0f}mm ({len(files)}\u5f20) ---')
            for fp in files[:5]:
                # 只显示文件名，不显示完整路径
                lines.append(f'  {os.path.basename(fp)}')
            if len(files) > 5:
                lines.append(f'  ...\u8fd8\u6709 {len(files)-5} \u5f20')
            lines.append('')

        return '\n'.join(lines)

    def update_status(self, text):
        Clock.schedule_once(lambda dt: setattr(self.status, 'text', text), 0)

    def update_result(self, text):
        Clock.schedule_once(lambda dt: setattr(self.result, 'text', text), 0)

if __name__ == '__main__':
    FocalStatsApp().run()
