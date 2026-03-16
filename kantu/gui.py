"""PySide6 GUI for KanTu with elegant modern design."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from kantu.api import (
    add_image,
    export_image,
    get_gallery_stats,
    init_gallery,
    list_images,
    remove_image,
)
from kantu.core import KanTuCore

MODERN_STYLE = """
QMainWindow {
    background-color: #0f0f23;
}
QWidget {
    background-color: transparent;
    color: #e0e0e0;
    font-family: 'SF Pro Display', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3a3a5c, stop:1 #2a2a4c);
    border: 1px solid #4a4a6c;
    border-radius: 8px;
    padding: 10px 20px;
    color: #ffffff;
    font-weight: 500;
    font-size: 13px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4a4a7c, stop:1 #3a3a6c);
    border: 1px solid #6a6a9c;
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a2a4c, stop:1 #1a1a3c);
}
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #764ba2);
    border: none;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7b8ffa, stop:1 #8a5bb3);
}
QPushButton#dangerBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f093fb, stop:1 #f5576c);
    border: none;
}
QPushButton#dangerBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f5a4fc, stop:1 #f6687d);
}
QTableWidget {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4e;
    border-radius: 12px;
    gridline-color: #2a2a4e;
    selection-background-color: #667eea;
    selection-color: white;
}
QTableWidget::item {
    padding: 12px 8px;
    border-bottom: 1px solid #2a2a4e;
}
QTableWidget::item:selected {
    background-color: rgba(102, 126, 234, 0.3);
}
QHeaderView::section {
    background-color: #16162a;
    color: #8888aa;
    padding: 14px 8px;
    border: none;
    border-bottom: 2px solid #667eea;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QScrollBar:vertical {
    background: #1a1a2e;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #4a4a6c;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #6a6a8c;
}
QProgressBar {
    background-color: #1a1a2e;
    border: none;
    border-radius: 6px;
    height: 8px;
    text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
    border-radius: 6px;
}
QStatusBar {
    background-color: #0a0a1a;
    border-top: 1px solid #2a2a4e;
    color: #888;
}
QLabel#titleLabel {
    font-size: 28px;
    font-weight: 700;
    color: #ffffff;
}
QLabel#subtitleLabel {
    font-size: 14px;
    color: #8888aa;
}
QLabel#statsLabel {
    font-size: 32px;
    font-weight: 700;
}
QLabel#statsDescLabel {
    font-size: 11px;
    color: #6666aa;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QFrame#cardFrame {
    background-color: #1a1a2e;
    border-radius: 16px;
    border: 1px solid #2a2a4e;
}
QFrame#previewFrame {
    background-color: #12121f;
    border-radius: 16px;
    border: 2px solid #2a2a4e;
}
"""


class StatsCard(QFrame):
    def __init__(self, title: str, value: str = "0", color: str = "#667eea"):
        super().__init__()
        self.setObjectName("cardFrame")
        self.setStyleSheet(f"QFrame#cardFrame {{ border-left: 4px solid {color}; }}")
        self.setFixedHeight(100)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("statsLabel")
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_label)
        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("statsDescLabel")
        layout.addWidget(self.title_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class ImagePreviewWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("previewFrame")
        self.setMinimumSize(400, 400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: transparent;")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.image_label)
        self.info_widget = QWidget()
        info_layout = QVBoxLayout(self.info_widget)
        info_layout.setContentsMargins(0, 15, 0, 0)
        self.id_label = QLabel("Select an image")
        self.id_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
        self.type_label = QLabel("")
        self.type_label.setStyleSheet("font-size: 13px; color: #8888aa;")
        self.dim_label = QLabel("")
        self.dim_label.setStyleSheet("font-size: 13px; color: #8888aa;")
        info_layout.addWidget(self.id_label)
        info_layout.addWidget(self.type_label)
        info_layout.addWidget(self.dim_label)
        layout.addWidget(self.info_widget)

    def set_image(self, pixmap: QPixmap, image_id: str, is_base: bool, width: int, height: int):
        if pixmap:
            scaled = pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
            self.id_label.setText(f"ID: {image_id[:16]}...")
            self.type_label.setText(f"Type: {'Base Image' if is_base else 'Delta Image'}")
            self.dim_label.setText(f"Dimensions: {width} × {height}")
        else:
            self.image_label.setText("Cannot preview")
            self.id_label.setText("Preview unavailable")
            self.type_label.setText("")
            self.dim_label.setText("")

    def clear(self):
        self.image_label.clear()
        self.image_label.setText("Select an image to preview")
        self.id_label.setText("Select an image")
        self.type_label.setText("")
        self.dim_label.setText("")


class MainWindow(QMainWindow):
    def __init__(self, gallery_path: str = "."):
        super().__init__()
        self.gallery_path = Path(gallery_path).resolve()
        self.setWindowTitle("KanTu")
        self.setMinimumSize(1400, 900)
        self.setStyleSheet(MODERN_STYLE)
        self.core = KanTuCore(str(self.gallery_path))
        self.setup_ui()
        self.refresh_gallery()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(30, 30, 30, 20)
        main_layout.setSpacing(20)
        header_layout = QVBoxLayout()
        title = QLabel("KanTu")
        title.setObjectName("titleLabel")
        header_layout.addWidget(title)
        subtitle = QLabel("Git-like Image Gallery Manager with Delta Encoding")
        subtitle.setObjectName("subtitleLabel")
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)
        self.stats_cards = {}
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)
        self.stats_cards["total"] = StatsCard("Total Images", "0", "#667eea")
        self.stats_cards["base"] = StatsCard("Base Images", "0", "#00d9ff")
        self.stats_cards["delta"] = StatsCard("Delta Images", "0", "#f093fb")
        self.stats_cards["saved"] = StatsCard("Storage Saved", "0%", "#00ff88")
        for card in self.stats_cards.values():
            stats_row.addWidget(card)
        main_layout.addLayout(stats_row)
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet(
            "QFrame { background-color: #1a1a2e; border-radius: 12px; padding: 5px; }"
        )
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(15, 10, 15, 10)
        self.btn_init = QPushButton("✦  Initialize Gallery")
        self.btn_init.setObjectName("primaryBtn")
        self.btn_init.clicked.connect(self.init_gallery_dialog)
        toolbar_layout.addWidget(self.btn_init)
        self.btn_add = QPushButton("➕  Add Images")
        self.btn_add.setObjectName("primaryBtn")
        self.btn_add.clicked.connect(self.add_images_dialog)
        toolbar_layout.addWidget(self.btn_add)
        self.btn_refresh = QPushButton("↻  Refresh")
        self.btn_refresh.clicked.connect(self.refresh_gallery)
        toolbar_layout.addWidget(self.btn_refresh)
        toolbar_layout.addStretch()
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedWidth(200)
        toolbar_layout.addWidget(self.progress)
        main_layout.addWidget(toolbar_frame)
        content_frame = QFrame()
        content_frame.setStyleSheet("QFrame { background-color: transparent; }")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_split = QHBoxLayout()
        content_split.setSpacing(20)
        table_frame = QFrame()
        table_frame.setStyleSheet("QFrame { background-color: #1a1a2e; border-radius: 12px; }")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.image_table = QTableWidget()
        self.image_table.setColumnCount(5)
        self.image_table.setHorizontalHeaderLabels(
            ["ID", "Type", "Dimensions", "Size", "Similarity"]
        )
        self.image_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.image_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.image_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.image_table.setShowGrid(False)
        self.image_table.verticalHeader().setVisible(False)
        self.image_table.itemSelectionChanged.connect(self.on_selection_changed)
        table_layout.addWidget(self.image_table)
        action_frame = QFrame()
        action_frame.setStyleSheet("QFrame { background-color: transparent; padding: 10px; }")
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(10, 10, 10, 10)
        self.btn_export = QPushButton("↓  Export Selected")
        self.btn_export.clicked.connect(self.export_selected)
        action_layout.addWidget(self.btn_export)
        self.btn_remove = QPushButton("✕  Remove Selected")
        self.btn_remove.setObjectName("dangerBtn")
        self.btn_remove.clicked.connect(self.remove_selected)
        action_layout.addWidget(self.btn_remove)
        action_layout.addStretch()
        table_layout.addWidget(action_frame)
        content_split.addWidget(table_frame, 2)
        self.preview_widget = ImagePreviewWidget()
        content_split.addWidget(self.preview_widget, 1)
        main_layout.addLayout(content_split, 1)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(f"Gallery: {self.gallery_path}")

    def init_gallery_dialog(self):
        result = init_gallery(str(self.gallery_path))
        if result.success:
            self.show_message("Success", "Gallery initialized successfully", "info")
            self.refresh_gallery()
        else:
            self.show_message("Error", result.error, "error")

    def add_images_dialog(self):
        if not self.core.is_initialized():
            self.show_message(
                "Warning", "Gallery not initialized. Click 'Initialize Gallery' first.", "warning"
            )
            return
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)",
        )
        if files:
            self.progress.setVisible(True)
            self.progress.setMaximum(len(files))
            self.progress.setValue(0)
            for i, file_path in enumerate(files):
                result = add_image(file_path, str(self.gallery_path))
                if not result.success:
                    self.show_message(
                        "Error", f"Failed to add {Path(file_path).name}:\n{result.error}", "error"
                    )
                self.progress.setValue(i + 1)
            self.progress.setVisible(False)
            self.refresh_gallery()

    def refresh_gallery(self):
        if not self.core.is_initialized():
            for card in self.stats_cards.values():
                card.set_value("—")
            return
        result = list_images(str(self.gallery_path), limit=1000)
        if result.success:
            images = result.data.get("images", [])
            self.image_table.setRowCount(len(images))
            for row, img in enumerate(images):
                id_item = QTableWidgetItem(img["id"][:16])
                id_item.setForeground(QColor("#667eea"))
                self.image_table.setItem(row, 0, id_item)
                is_base = img["is_base"]
                type_text = "◉ Base" if is_base else "◈ Delta"
                type_item = QTableWidgetItem(type_text)
                type_item.setForeground(QColor("#00d9ff" if is_base else "#f093fb"))
                self.image_table.setItem(row, 1, type_item)
                self.image_table.setItem(
                    row, 2, QTableWidgetItem(f"{img['width']} × {img['height']}")
                )
                self.image_table.setItem(
                    row, 3, QTableWidgetItem(self._format_size(img["file_size"]))
                )
                similarity = img.get("similarity_score", 1.0) if not is_base else 1.0
                sim_item = QTableWidgetItem(f"{similarity:.1%}")
                sim_item.setForeground(QColor("#00ff88" if similarity > 0.9 else "#ffaa00"))
                self.image_table.setItem(row, 4, sim_item)
        stats_result = get_gallery_stats(str(self.gallery_path))
        if stats_result.success:
            stats = stats_result.data
            self.stats_cards["total"].set_value(str(stats["total_images"]))
            self.stats_cards["base"].set_value(str(stats["base_images"]))
            self.stats_cards["delta"].set_value(str(stats["delta_images"]))
            self.stats_cards["saved"].set_value(f"{stats['savings_ratio']:.1%}")
            self.status_bar.showMessage(
                f"Gallery: {self.gallery_path} | "
                f"Total: {self._format_size(stats['total_size'])} | "
                f"Saved: {stats['savings_ratio']:.1%}"
            )

    def on_selection_changed(self):
        selected = self.image_table.selectedItems()
        if not selected:
            self.preview_widget.clear()
            return
        row = selected[0].row()
        image_id_item = self.image_table.item(row, 0)
        if image_id_item:
            image_id = image_id_item.text()
            self.show_image_preview(image_id)

    def show_image_preview(self, image_id: str):
        if not self.core.is_initialized():
            return
        arr = self.core.reconstruct_image(image_id)
        record = self.core.get_image_record(image_id)
        if arr is not None and record:
            h, w = arr.shape[:2]
            if len(arr.shape) == 3:
                ch = arr.shape[2]
                if ch == 3:
                    qimg = QImage(arr.data, w, h, 3 * w, QImage.Format_RGB888)
                elif ch == 4:
                    qimg = QImage(arr.data, w, h, 4 * w, QImage.Format_RGBA8888)
                else:
                    qimg = QImage(arr.data, w, h, w, QImage.Format_Grayscale8)
            else:
                qimg = QImage(arr.data, w, h, w, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(qimg)
            self.preview_widget.set_image(
                pixmap, image_id, record["is_base"], record["width"], record["height"]
            )
        else:
            self.preview_widget.clear()

    def export_selected(self):
        selected = self.image_table.selectedItems()
        if not selected:
            self.show_message("Warning", "No image selected", "warning")
            return
        row = selected[0].row()
        image_id_item = self.image_table.item(row, 0)
        if not image_id_item:
            return
        image_id = image_id_item.text()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Image", f"{image_id}.png", "PNG (*.png);;JPEG (*.jpg)"
        )
        if file_path:
            result = export_image(image_id, file_path, str(self.gallery_path))
            if result.success:
                self.show_message("Success", f"Image exported to {file_path}", "info")
            else:
                self.show_message("Error", result.error, "error")

    def remove_selected(self):
        selected = self.image_table.selectedItems()
        if not selected:
            self.show_message("Warning", "No image selected", "warning")
            return
        row = selected[0].row()
        image_id_item = self.image_table.item(row, 0)
        if not image_id_item:
            return
        image_id = image_id_item.text()
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove image {image_id[:16]}...?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            result = remove_image(image_id, str(self.gallery_path))
            if result.success:
                self.refresh_gallery()
                self.preview_widget.clear()
            else:
                self.show_message("Error", result.error, "error")

    def show_message(self, title: str, message: str, msg_type: str = "info"):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(message)
        if msg_type == "error":
            box.setIcon(QMessageBox.Critical)
        elif msg_type == "warning":
            box.setIcon(QMessageBox.Warning)
        else:
            box.setIcon(QMessageBox.Information)
        box.setStyleSheet("""
            QMessageBox {
                background-color: #1a1a2e;
            }
            QMessageBox QLabel {
                color: #e0e0e0;
                font-size: 14px;
            }
            QPushButton {
                background-color: #667eea;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #7b8ffa;
            }
        """)
        box.exec()

    def _format_size(self, size: int) -> str:
        s = float(size)
        for unit in ["B", "KB", "MB", "GB"]:
            if s < 1024:
                return f"{s:.1f} {unit}"
            s /= 1024
        return f"{s:.1f} TB"

    def closeEvent(self, event):
        self.core.close()
        event.accept()


def run_gui(gallery_path: str = ".", no_web: bool = False):
    app = QApplication(sys.argv)
    app.setApplicationName("KanTu")
    app.setStyle("Fusion")
    window = MainWindow(gallery_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
