import sys
import os
import re
import json
import datetime
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtWidgets import ( # type: ignore
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog, QMessageBox,
    QGroupBox, QComboBox, QTabWidget, QProgressBar, QSplitter,
    QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtGui import QFont, QDropEvent, QDragEnterEvent, QPalette, QColor # type: ignore
from PySide6.QtCore import Qt, QObject, Signal, QThread, QRunnable, QThreadPool, Slot # type: ignore

import matplotlib # type: ignore
matplotlib.use("Agg")
import matplotlib.pyplot as plt # type: ignore
import matplotlib.patches as mpatches # type: ignore
from matplotlib.figure import Figure # type: ignore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas # type: ignore
import io
from PySide6.QtGui import QPixmap, QImage # type: ignore


# ==========================================
# سیستم مدیریت زبان با اسکن پوشه محلی (i18n)
# ==========================================
class LangManager(QObject):
    lang_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.available_langs = {}
        self.translations = {}
        self.current_lang = "fa"

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.locales_dir = os.path.join(base_dir, "locales")

        self.scan_languages()
        self.load_language(self.current_lang)

    def scan_languages(self):
        if not os.path.exists(self.locales_dir):
            os.makedirs(self.locales_dir)
            return

        for filename in os.listdir(self.locales_dir):
            if filename.endswith(".json"):
                lang_code = filename[:-5]
                filepath = os.path.join(self.locales_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        lang_name = data.get("lang_name", lang_code.upper())
                        self.available_langs[lang_code] = lang_name
                except Exception as e:
                    print(f"Error reading {filename}: {e}")

        if not self.available_langs:
            self.available_langs["fa"] = "فارسی"
            self.available_langs["en"] = "English"

    def load_language(self, lang_code):
        filepath = os.path.join(self.locales_dir, f"{lang_code}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
                self.current_lang = lang_code
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
        else:
            self.translations = {}
            self.current_lang = lang_code

    def set_lang(self, lang_code):
        if lang_code != self.current_lang:
            self.load_language(lang_code)
            direction = Qt.RightToLeft if lang_code in ["fa", "ar", "he"] else Qt.LeftToRight
            QApplication.instance().setLayoutDirection(direction)
            self.lang_changed.emit(self.current_lang)

    def t(self, key, *args):
        val = self.translations.get(key, key)
        if args:
            try:
                return val.format(*args)
            except Exception:
                return val
        return val


# ==========================================
# Worker: پردازش در thread جداگانه
# ==========================================
class AnalysisSignals(QObject):
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(int)


class AnalysisWorker(QRunnable):
    def __init__(self, source: str, is_file: bool, exclude_set: set):
        super().__init__()
        self.source = source
        self.is_file = is_file
        self.exclude_set = exclude_set
        self.signals = AnalysisSignals()

    @Slot()
    def run(self):
        try:
            self.signals.progress.emit(10)

            if self.is_file:
                with open(self.source, "r", encoding="utf-8") as f:
                    content = f.read()
                source_name = os.path.basename(self.source)
            else:
                content = self.source
                source_name = "direct_input"

            self.signals.progress.emit(30)

            # استفاده از regex برای جداسازی صحیح کلمات (پشتیبانی یونیکد)
            all_words = re.findall(r'\b\w+\b', content, re.UNICODE)
            chars_count = len(content)
            lines_count = content.count('\n') + 1

            self.signals.progress.emit(50)

            filtered_words = [w for w in all_words if w.lower() not in self.exclude_set]
            excluded_count = len(all_words) - len(filtered_words)

            total_word_count = len(filtered_words)
            unique_words_count = len(set(w.lower() for w in filtered_words))
            avg_word_length = (
                sum(len(w) for w in filtered_words) / total_word_count
                if total_word_count > 0 else 0
            )

            self.signals.progress.emit(70)

            word_counts = Counter(w.lower() for w in filtered_words)
            most_common_words = word_counts.most_common(10)

            self.signals.progress.emit(100)

            self.signals.finished.emit({
                "source_name": source_name,
                "total_words": total_word_count,
                "unique_words": unique_words_count,
                "lines_count": lines_count,
                "chars_count": chars_count,
                "avg_word_length": avg_word_length,
                "excluded_count": excluded_count,
                "most_common": most_common_words,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

        except Exception as e:
            self.signals.error.emit(str(e))


# ==========================================
# نمودار matplotlib
# ==========================================
class ChartWidget(QLabel):
    """یه QLabel که تصویر matplotlib رو نمایش میده"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(250)
        self.setText("📊")
        self.setStyleSheet("font-size: 40pt; color: #555;")

    def plot(self, words_data: list, is_dark: bool, lang_code: str):
        if not words_data:
            return

        words = [w for w, _ in words_data]
        counts = [c for _, c in words_data]

        fig = Figure(figsize=(6, 3.5), dpi=100)
        fig.patch.set_facecolor("#1e1f22" if is_dark else "#f5f5f5")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#282a2e" if is_dark else "#ffffff")

        colors = ["#ff6808", "#ff8c42", "#ffa566", "#ffbe8a", "#ffd4ae",
                  "#e05500", "#cc4400", "#b83300", "#a42200", "#901100"]
        bars = ax.barh(words, counts, color=colors[:len(words)], edgecolor="none", height=0.6)

        text_color = "#c5c8c6" if is_dark else "#222"
        ax.tick_params(colors=text_color, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#3c3f41" if is_dark else "#ccc")

        ax.set_xlabel("count" if lang_code not in ["fa", "ar"] else "ﺩﺍﺪﻌﺗ",
                      color=text_color, fontsize=9)
        ax.invert_yaxis()

        for bar, count in zip(bars, counts):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                    str(count), va='center', color=text_color, fontsize=8)

        fig.tight_layout(pad=1.2)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)

        img = QImage.fromData(buf.read())
        pixmap = QPixmap.fromImage(img)
        self.setPixmap(pixmap.scaled(
            self.width() or 500, self.height() or 300,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        self.setStyleSheet("")


# ==========================================
# کارت تاریخچه
# ==========================================
class HistoryCard(QFrame):
    clicked = Signal(dict)

    def __init__(self, result: dict, lang_mgr, parent=None):
        super().__init__(parent)
        self.result = result
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(72)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        top = QHBoxLayout()
        name_lbl = QLabel(result["source_name"])
        name_lbl.setStyleSheet("font-weight: bold; font-size: 10pt;")
        top.addWidget(name_lbl)
        top.addStretch()
        time_lbl = QLabel(result["timestamp"])
        time_lbl.setStyleSheet("font-size: 8pt; color: #888;")
        top.addWidget(time_lbl)
        layout.addLayout(top)

        stats = QLabel(
            f"{lang_mgr.t('total_words').split(':')[0]}: {result['total_words']}  |  "
            f"{lang_mgr.t('unique_words').split(':')[0]}: {result['unique_words']}"
        )
        stats.setStyleSheet("font-size: 9pt; color: #aaa;")
        layout.addWidget(stats)

    def mousePressEvent(self, event):
        self.clicked.emit(self.result)


# ==========================================
# DropLineEdit
# ==========================================
class DropLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        url = event.mimeData().urls()[0]
        if url.isLocalFile():
            self.setText(url.toLocalFile())


# ==========================================
# استایل‌ها
# ==========================================
DARK_STYLE = """
QWidget {
    font-family: "Vazir", "Segoe UI", sans-serif;
    font-size: 11pt;
}
QPushButton {
    background-color: #ff6808;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 5px;
    font-weight: bold;
}
QPushButton:hover { background-color: #ff5808; }
QPushButton#saveButton { background-color: #f39c12; }
QPushButton#saveButton:hover { background-color: #e67e22; }
QLabel#titleLabel {
    font-size: 18pt;
    font-weight: bold;
    color: #ff5808;
}
QGroupBox {
    border: 1px solid #3c3f41;
    border-radius: 5px;
    margin-top: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 10px;
}
QTabWidget::pane { border: 1px solid #3c3f41; border-radius: 5px; }
QTabBar::tab {
    padding: 6px 18px;
    border-radius: 4px 4px 0 0;
    font-weight: bold;
}
QTabBar::tab:selected { background: #ff6808; color: white; }
QProgressBar {
    border: 1px solid #3c3f41;
    border-radius: 4px;
    text-align: center;
    height: 14px;
}
QProgressBar::chunk { background-color: #ff6808; border-radius: 3px; }
"""


# ==========================================
# پنجره اصلی
# ==========================================
class AdvancedWordCounter(QMainWindow):
    def __init__(self, lang_mgr_instance: LangManager):
        super().__init__()
        self.lang_mgr = lang_mgr_instance   # تزریق وابستگی به جای global
        self.setGeometry(100, 100, 820, 720)
        self.setAcceptDrops(True)
        self.last_result: dict = {}
        self.history: list = []
        self.is_dark_mode = True
        self.thread_pool = QThreadPool()

        self.init_ui()
        self.apply_theme()
        self.lang_mgr.lang_changed.connect(self.update_texts)
        self.update_texts()

    # ------------------------------------------
    # ساخت UI
    # ------------------------------------------
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)

        # ---- نوار بالایی ----
        top_bar = QHBoxLayout()

        self.theme_btn = QPushButton()
        self.theme_btn.setFixedWidth(120)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        top_bar.addWidget(self.theme_btn)

        self.lang_combo = QComboBox()
        self.lang_combo.setCursor(Qt.PointingHandCursor)
        self.lang_combo.setFixedWidth(110)
        self.lang_combo.setStyleSheet("QComboBox { padding: 4px; font-weight: bold; }")
        for code, name in self.lang_mgr.available_langs.items():
            self.lang_combo.addItem(name, code)
        idx = self.lang_combo.findData(self.lang_mgr.current_lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        top_bar.addWidget(self.lang_combo)

        top_bar.addStretch()

        self.title = QLabel()
        self.title.setObjectName("titleLabel")
        self.title.setAlignment(Qt.AlignCenter)
        top_bar.addWidget(self.title)

        top_bar.addStretch()
        root.addLayout(top_bar)

        # ---- تب‌ها ----
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self.tabs.addTab(self._build_file_tab(), "📂")
        self.tabs.addTab(self._build_direct_tab(), "✏️")
        self.tabs.addTab(self._build_history_tab(), "🕑")

        # ---- progress bar ----
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(100)
        root.addWidget(self.progress_bar)

        # ---- بخش نتایج ----
        self.result_group = QGroupBox()
        result_layout = QVBoxLayout(self.result_group)

        splitter = QSplitter(Qt.Horizontal)

        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        self.result_display.setMinimumWidth(280)
        splitter.addWidget(self.result_display)

        self.chart_widget = ChartWidget()
        splitter.addWidget(self.chart_widget)
        splitter.setSizes([320, 480])

        result_layout.addWidget(splitter)

        action_layout = QHBoxLayout()
        self.copy_button = QPushButton()
        self.copy_button.clicked.connect(self.copy_results)
        action_layout.addWidget(self.copy_button)

        self.save_button = QPushButton()
        self.save_button.setObjectName("saveButton")
        self.save_button.clicked.connect(self.save_output)
        action_layout.addWidget(self.save_button)

        result_layout.addLayout(action_layout)
        root.addWidget(self.result_group)

    def _build_file_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        self.file_input_group = QGroupBox()
        input_layout = QVBoxLayout(self.file_input_group)

        self.file_path_edit = DropLineEdit()
        input_layout.addWidget(self.file_path_edit)

        self.browse_button = QPushButton()
        self.browse_button.clicked.connect(self.browse_file)
        input_layout.addWidget(self.browse_button)

        self.filter_lbl = QLabel()
        input_layout.addWidget(self.filter_lbl)

        self.exclude_edit = QLineEdit()
        input_layout.addWidget(self.exclude_edit)

        layout.addWidget(self.file_input_group)

        self.count_button = QPushButton()
        self.count_button.setFixedHeight(40)
        self.count_button.clicked.connect(lambda: self.process_text(from_file=True))
        layout.addWidget(self.count_button)

        return w

    def _build_direct_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        self.direct_input_group = QGroupBox()
        direct_layout = QVBoxLayout(self.direct_input_group)

        self.direct_text_edit = QTextEdit()
        self.direct_text_edit.setPlaceholderText("...")
        self.direct_text_edit.setMinimumHeight(150)
        direct_layout.addWidget(self.direct_text_edit)

        self.filter_lbl2 = QLabel()
        direct_layout.addWidget(self.filter_lbl2)

        self.exclude_edit2 = QLineEdit()
        direct_layout.addWidget(self.exclude_edit2)

        layout.addWidget(self.direct_input_group)

        self.count_button2 = QPushButton()
        self.count_button2.setFixedHeight(40)
        self.count_button2.clicked.connect(lambda: self.process_text(from_file=False))
        layout.addWidget(self.count_button2)

        return w

    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.history_group = QGroupBox()
        group_layout = QVBoxLayout(self.history_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.addStretch()
        scroll.setWidget(self.history_container)
        group_layout.addWidget(scroll)

        self.clear_history_btn = QPushButton()
        self.clear_history_btn.clicked.connect(self.clear_history)
        group_layout.addWidget(self.clear_history_btn)

        layout.addWidget(self.history_group)
        return w

    # ------------------------------------------
    # رویدادها و منطق
    # ------------------------------------------
    def change_language(self, index):
        code = self.lang_combo.itemData(index)
        if code:
            self.lang_mgr.set_lang(code)

    def update_texts(self):
        self.setWindowTitle(self.lang_mgr.t("app_title"))
        self.title.setText(self.lang_mgr.t("title_label"))

        # تب ۱: فایل
        self.file_input_group.setTitle(self.lang_mgr.t("input_group"))
        self.browse_button.setText(self.lang_mgr.t("browse_btn"))
        self.filter_lbl.setText(self.lang_mgr.t("filter_label"))
        self.exclude_edit.setPlaceholderText(self.lang_mgr.t("filter_placeholder"))
        self.count_button.setText(self.lang_mgr.t("calc_btn"))
        self.file_path_edit.setPlaceholderText(self.lang_mgr.t("file_placeholder") if self.lang_mgr.t("file_placeholder") != "file_placeholder" else "drag & drop ...")

        # تب ۲: مستقیم
        self.direct_input_group.setTitle(self.lang_mgr.t("direct_input_group") if self.lang_mgr.t("direct_input_group") != "direct_input_group" else "Direct Text Input")
        self.filter_lbl2.setText(self.lang_mgr.t("filter_label"))
        self.exclude_edit2.setPlaceholderText(self.lang_mgr.t("filter_placeholder"))
        self.count_button2.setText(self.lang_mgr.t("calc_btn"))

        # تب ۳: تاریخچه
        self.history_group.setTitle(self.lang_mgr.t("history_group") if self.lang_mgr.t("history_group") != "history_group" else "History")
        self.clear_history_btn.setText(self.lang_mgr.t("clear_history_btn") if self.lang_mgr.t("clear_history_btn") != "clear_history_btn" else "Clear History")

        # نتایج
        self.result_group.setTitle(self.lang_mgr.t("result_group"))
        self.copy_button.setText(self.lang_mgr.t("copy_btn"))
        self.save_button.setText(self.lang_mgr.t("save_btn"))

        # تب‌ها
        self.tabs.setTabText(0, self.lang_mgr.t("tab_file") if self.lang_mgr.t("tab_file") != "tab_file" else f"📂 {self.lang_mgr.t('input_group')}")
        self.tabs.setTabText(1, self.lang_mgr.t("tab_direct") if self.lang_mgr.t("tab_direct") != "tab_direct" else "✏️ Direct")
        self.tabs.setTabText(2, self.lang_mgr.t("tab_history") if self.lang_mgr.t("tab_history") != "tab_history" else "🕑 History")

        # دکمه تم: از i18n بخون، اگه نبود fallback
        theme_key = "theme_dark_btn" if self.is_dark_mode else "theme_light_btn"
        theme_fallback = "☀️ Light" if self.is_dark_mode else "🌙 Dark"
        raw = self.lang_mgr.t(theme_key)
        self.theme_btn.setText(raw if raw != theme_key else theme_fallback)

    # ------------------------------------------
    # drag & drop روی پنجره اصلی
    # ------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        url = event.mimeData().urls()[0]
        if url.isLocalFile():
            self.file_path_edit.setText(url.toLocalFile())
            self.tabs.setCurrentIndex(0)

    # ------------------------------------------
    # تم
    # ------------------------------------------
    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()
        self.update_texts()
        if self.last_result:
            self.chart_widget.plot(
                self.last_result.get("most_common", []),
                self.is_dark_mode,
                self.lang_mgr.current_lang
            )

    def apply_theme(self):
        palette = QPalette()
        if self.is_dark_mode:
            palette.setColor(QPalette.Window, QColor("#16171a"))
            palette.setColor(QPalette.WindowText, QColor("#c5c8c6"))
            palette.setColor(QPalette.Base, QColor("#282a2e"))
            palette.setColor(QPalette.Text, QColor("#c5c8c6"))
            self.setStyleSheet(
                DARK_STYLE +
                "\nQWidget { background-color: #1e1f22; color: #c5c8c6; }"
                " QMainWindow { background-color: #16171a; }"
                " QLineEdit, QTextEdit { background-color: #282a2e; border: 1px solid #3c3f41; }"
                " QFrame { border: 1px solid #3c3f41; border-radius: 5px; background: #282a2e; }"
                " QScrollArea { border: none; }"
            )
            self.theme_btn.setStyleSheet(
                "background-color: #3a3b3c; color: white; font-size: 10pt; padding: 5px; border-radius: 5px;"
            )
        else:
            palette.setColor(QPalette.Window, QColor("#f5f5f5"))
            palette.setColor(QPalette.WindowText, QColor("#000000"))
            palette.setColor(QPalette.Base, QColor("#ffffff"))
            palette.setColor(QPalette.Text, QColor("#000000"))
            self.setStyleSheet(
                DARK_STYLE +
                "\nQWidget { background-color: #f5f5f5; color: #000000; }"
                " QMainWindow { background-color: #e0e0e0; }"
                " QLineEdit, QTextEdit { background-color: #ffffff; border: 1px solid #bdc3c7; color: #000000; }"
                " QFrame { border: 1px solid #bdc3c7; border-radius: 5px; background: #ffffff; }"
                " QScrollArea { border: none; }"
            )
            self.theme_btn.setStyleSheet(
                "background-color: white; color: black; font-size: 10pt; padding: 5px;"
                " border: 1px solid #bdc3c7; border-radius: 5px;"
            )
        QApplication.instance().setPalette(palette)

    # ------------------------------------------
    # Browse
    # ------------------------------------------
    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            self.lang_mgr.t("browse_btn"),
            "",
            "Text Files (*.txt *.md);;All Files (*)"
        )
        if file_name:
            self.file_path_edit.setText(file_name)
            self.result_display.clear()

    # ------------------------------------------
    # پردازش متن (در thread جداگانه)
    # ------------------------------------------
    def process_text(self, from_file: bool):
        exclude_set = set()

        if from_file:
            file_path = self.file_path_edit.text()
            exc_text = self.exclude_edit.text()
            if not file_path or not os.path.exists(file_path):
                QMessageBox.warning(self, self.lang_mgr.t("error_title"), self.lang_mgr.t("valid_file_msg"))
                return
            if not os.path.isfile(file_path) or os.path.getsize(file_path) == 0:
                QMessageBox.warning(self, self.lang_mgr.t("error_title"), self.lang_mgr.t("empty_file_msg"))
                return
            exclude_set = {w.strip().lower() for w in exc_text.split(',') if w.strip()}
            worker = AnalysisWorker(file_path, True, exclude_set)
        else:
            text = self.direct_text_edit.toPlainText().strip()
            exc_text = self.exclude_edit2.text()
            if not text:
                QMessageBox.warning(self, self.lang_mgr.t("error_title"),
                                    self.lang_mgr.t("empty_direct_msg") if self.lang_mgr.t("empty_direct_msg") != "empty_direct_msg" else "Please enter some text.")
                return
            exclude_set = {w.strip().lower() for w in exc_text.split(',') if w.strip()}
            worker = AnalysisWorker(text, False, exclude_set)

        worker.signals.finished.connect(self.on_analysis_done)
        worker.signals.error.connect(self.on_analysis_error)
        worker.signals.progress.connect(self.on_progress)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.count_button.setEnabled(False)
        self.count_button2.setEnabled(False)

        self.thread_pool.start(worker)

    @Slot(dict)
    def on_analysis_done(self, result: dict):
        self.progress_bar.setVisible(False)
        self.count_button.setEnabled(True)
        self.count_button2.setEnabled(True)
        self.last_result = result

        self._render_result(result)
        self.chart_widget.plot(
            result.get("most_common", []),
            self.is_dark_mode,
            self.lang_mgr.current_lang
        )
        self._add_to_history(result)

    @Slot(str)
    def on_analysis_error(self, msg: str):
        self.progress_bar.setVisible(False)
        self.count_button.setEnabled(True)
        self.count_button2.setEnabled(True)
        QMessageBox.critical(self, "Error", msg)

    @Slot(int)
    def on_progress(self, val: int):
        self.progress_bar.setValue(val)

    def _render_result(self, r: dict):
        lm = self.lang_mgr
        lines = [
            lm.t("analysis_res").format(r["source_name"]),
            "-" * 30,
            lm.t("total_words").format(r["total_words"]),
            lm.t("unique_words").format(r["unique_words"]),
            lm.t("lines_count").format(r["lines_count"]),
            lm.t("chars_count").format(r["chars_count"]),
            lm.t("avg_len").format(f"{r['avg_word_length']:.2f}"),
            lm.t("filtered_count").format(r["excluded_count"]),
            lm.t("top_words"),
        ]
        for i, (word, count) in enumerate(r["most_common"], 1):
            lines.append(f"  {i}. \"{word}\" ({count} {lm.t('times')})")

        text = "\n".join(lines)
        self.result_display.setText(text)
        self.last_result["_rendered"] = text

    # ------------------------------------------
    # تاریخچه
    # ------------------------------------------
    def _add_to_history(self, result: dict):
        self.history.insert(0, result)

        card = HistoryCard(result, self.lang_mgr)
        card.clicked.connect(self._load_from_history)

        # درج در ابتدای لیست (قبل از stretch)
        self.history_layout.insertWidget(0, card)

    def _load_from_history(self, result: dict):
        self.last_result = result
        self._render_result(result)
        self.chart_widget.plot(
            result.get("most_common", []),
            self.is_dark_mode,
            self.lang_mgr.current_lang
        )
        self.tabs.setCurrentIndex(0)

    def clear_history(self):
        self.history.clear()
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ------------------------------------------
    # کپی و ذخیره
    # ------------------------------------------
    def copy_results(self):
        text = self.last_result.get("_rendered", "")
        if not text:
            QMessageBox.warning(self, self.lang_mgr.t("attention_title"), self.lang_mgr.t("analyze_first"))
            return
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, self.lang_mgr.t("success_title"), self.lang_mgr.t("copied_msg"))

    def save_output(self):
        text = self.last_result.get("_rendered", "")
        if not text:
            QMessageBox.warning(self, self.lang_mgr.t("attention_title"), self.lang_mgr.t("analyze_first"))
            return

        full_output = (
            f"{text}\n\n"
            f"---------------------------------\n"
            f"Date: {self.last_result.get('timestamp', '')}\n"
            f"Source: {self.last_result.get('source_name', '')}"
        )

        save_path, _ = QFileDialog.getSaveFileName(self, self.lang_mgr.t("save_btn"), "", "Text Files (*.txt)")
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(full_output)
                QMessageBox.information(self, self.lang_mgr.t("success_title"), self.lang_mgr.t("saved_msg"))
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))


# ==========================================
# نقطه ورود
# ==========================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    lang_mgr = LangManager()

    initial_direction = Qt.RightToLeft if lang_mgr.current_lang in ["fa", "ar", "he"] else Qt.LeftToRight
    app.setLayoutDirection(initial_direction)

    window = AdvancedWordCounter(lang_mgr)
    window.show()
    sys.exit(app.exec())
