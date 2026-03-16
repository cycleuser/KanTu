"""PySide6 GUI for KanTu."""

import sys
from pathlib import Path
from typing import override

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
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


class WorkerThread(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self, gallery_path: str = "."):
        super().__init__()
        self.gallery_path = Path(gallery_path).resolve()
        self.setWindowTitle(f"KanTu - Image Gallery Manager [{self.gallery_path}]")
        self.setMinimumSize(1200, 800)
        self.core = KanTuCore(str(self.gallery_path))
        self.init_ui()
        self.refresh_gallery()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        toolbar = QHBoxLayout()
        self.btn_init = QPushButton("Init Gallery")
        self.btn_init.clicked.connect(self.init_gallery_dialog)
        toolbar.addWidget(self.btn_init)
        self.btn_add = QPushButton("Add Images")
        self.btn_add.clicked.connect(self.add_images_dialog)
        toolbar.addWidget(self.btn_add)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh_gallery)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addStretch()
        self.stats_label = QLabel()
        toolbar.addWidget(self.stats_label)
        main_layout.addLayout(toolbar)
        splitter = QSplitter(Qt.Horizontal)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        self.image_table = QTableWidget()
        self.image_table.setColumnCount(6)
        self.image_table.setHorizontalHeaderLabels(
            ["ID", "Type", "Dimensions", "Size", "Similarity", "Base ID"]
        )
        self.image_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.image_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.image_table.itemSelectionChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.image_table)
        btn_layout = QHBoxLayout()
        self.btn_export = QPushButton("Export Selected")
        self.btn_export.clicked.connect(self.export_selected)
        btn_layout.addWidget(self.btn_export)
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.clicked.connect(self.remove_selected)
        btn_layout.addWidget(self.btn_remove)
        left_layout.addLayout(btn_layout)
        splitter.addWidget(left_panel)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.image_label = QLabel("Select an image to preview")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setStyleSheet("background-color: #f0f0f0;")
        right_layout.addWidget(self.image_label)
        self.info_label = QLabel()
        right_layout.addWidget(self.info_label)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 400])
        main_layout.addWidget(splitter)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        main_layout.addWidget(self.progress)

    def init_gallery_dialog(self):
        result = init_gallery(str(self.gallery_path))
        if result.success:
            QMessageBox.information(self, "Success", "Gallery initialized successfully")
            self.refresh_gallery()
        else:
            QMessageBox.warning(self, "Error", result.error)

    def add_images_dialog(self):
        if not self.core.is_initialized():
            QMessageBox.warning(
                self, "Error", "Gallery not initialized. Click 'Init Gallery' first."
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
                    QMessageBox.warning(
                        self, "Error", f"Failed to add {file_path}:\n{result.error}"
                    )
                self.progress.setValue(i + 1)
            self.progress.setVisible(False)
            self.refresh_gallery()

    def refresh_gallery(self):
        if not self.core.is_initialized():
            self.stats_label.setText("Not initialized")
            return
        result = list_images(str(self.gallery_path), limit=1000)
        if result.success:
            images = result.data.get("images", [])
            self.image_table.setRowCount(len(images))
            for row, img in enumerate(images):
                self.image_table.setItem(row, 0, QTableWidgetItem(img["id"][:12]))
                self.image_table.setItem(
                    row, 1, QTableWidgetItem("Base" if img["is_base"] else "Delta")
                )
                self.image_table.setItem(
                    row, 2, QTableWidgetItem(f"{img['width']}x{img['height']}")
                )
                self.image_table.setItem(
                    row, 3, QTableWidgetItem(self._format_size(img["file_size"]))
                )
                similarity = img.get("similarity_score", 1.0) if not img["is_base"] else 1.0
                self.image_table.setItem(row, 4, QTableWidgetItem(f"{similarity:.1%}"))
                base_id = img.get("base_id", "")[:12] if img.get("base_id") else "-"
                self.image_table.setItem(row, 5, QTableWidgetItem(base_id))
        stats_result = get_gallery_stats(str(self.gallery_path))
        if stats_result.success:
            stats = stats_result.data
            self.stats_label.setText(
                f"Images: {stats['total_images']} | "
                f"Storage: {self._format_size(stats['total_size'])} | "
                f"Saved: {stats['savings_ratio']:.1%}"
            )

    def on_selection_changed(self):
        selected = self.image_table.selectedItems()
        if not selected:
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
        if arr is not None:
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
            scaled = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled)
            record = self.core.get_image_record(image_id)
            if record:
                self.info_label.setText(
                    f"ID: {image_id}\n"
                    f"Type: {'Base' if record['is_base'] else 'Delta'}\n"
                    f"Dimensions: {record['width']}x{record['height']}"
                )
        else:
            self.image_label.setText("Cannot preview image")

    def export_selected(self):
        selected = self.image_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Error", "No image selected")
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
                QMessageBox.information(self, "Success", f"Image exported to {file_path}")
            else:
                QMessageBox.warning(self, "Error", result.error)

    def remove_selected(self):
        selected = self.image_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Error", "No image selected")
            return
        row = selected[0].row()
        image_id_item = self.image_table.item(row, 0)
        if not image_id_item:
            return
        image_id = image_id_item.text()
        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Remove image {image_id}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            result = remove_image(image_id, str(self.gallery_path))
            if result.success:
                self.refresh_gallery()
            else:
                QMessageBox.warning(self, "Error", result.error)

    def _format_size(self, size: int) -> str:
        s = float(size)
        for unit in ["B", "KB", "MB", "GB"]:
            if s < 1024:
                return f"{s:.1f} {unit}"
            s /= 1024
        return f"{s:.1f} TB"

    @override
    def closeEvent(self, event):
        self.core.close()
        event.accept()


def run_gui(gallery_path: str = ".", no_web: bool = False):
    app = QApplication(sys.argv)
    app.setApplicationName("KanTu")
    window = MainWindow(gallery_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
