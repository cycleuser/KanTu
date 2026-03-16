"""PySide6 GUI for KanTu with native styling."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
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


class MainWindow(QMainWindow):
    def __init__(self, gallery_path: str = "."):
        super().__init__()
        self.gallery_path = Path(gallery_path).resolve()
        self.setWindowTitle(f"KanTu - {self.gallery_path}")
        self.setMinimumSize(1100, 700)
        self.core = KanTuCore(str(self.gallery_path))
        self.setup_ui()
        self.refresh_gallery()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        stats_group = QGroupBox("Gallery Statistics")
        stats_layout = QHBoxLayout(stats_group)
        stats_layout.setSpacing(20)
        self.stat_labels = {}
        for name, label in [
            ("Total", "Total Images"),
            ("Base", "Base Images"),
            ("Delta", "Delta Images"),
            ("Saved", "Storage Saved"),
        ]:
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(2)
            value_label = QLabel("0")
            value_label.setStyleSheet("font-size: 18px; font-weight: bold;")
            name_label = QLabel(label)
            name_label.setStyleSheet("color: gray; font-size: 11px;")
            container_layout.addWidget(value_label)
            container_layout.addWidget(name_label)
            self.stat_labels[name] = value_label
            stats_layout.addWidget(container)
        stats_layout.addStretch()
        main_layout.addWidget(stats_group)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)
        self.btn_init = QPushButton("Init Gallery")
        self.btn_init.clicked.connect(self.init_gallery_dialog)
        toolbar_layout.addWidget(self.btn_init)
        self.btn_add = QPushButton("Add Images")
        self.btn_add.clicked.connect(self.add_images_dialog)
        toolbar_layout.addWidget(self.btn_add)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh_gallery)
        toolbar_layout.addWidget(self.btn_refresh)
        toolbar_layout.addStretch()
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedWidth(150)
        toolbar_layout.addWidget(self.progress)
        main_layout.addLayout(toolbar_layout)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.image_table = QTableWidget()
        self.image_table.setColumnCount(5)
        self.image_table.setHorizontalHeaderLabels(
            ["ID", "Type", "Dimensions", "Size", "Similarity"]
        )
        self.image_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.image_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.image_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.image_table.setAlternatingRowColors(True)
        self.image_table.itemSelectionChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.image_table)

        action_layout = QHBoxLayout()
        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self.export_selected)
        action_layout.addWidget(self.btn_export)
        self.btn_remove = QPushButton("Remove")
        self.btn_remove.clicked.connect(self.remove_selected)
        action_layout.addWidget(self.btn_remove)
        action_layout.addStretch()
        left_layout.addLayout(action_layout)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.image_label = QLabel("Select an image")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(300, 300)
        self.image_label.setStyleSheet("background-color: palette(base);")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_layout.addWidget(self.image_label)
        right_layout.addWidget(preview_group)

        info_group = QGroupBox("Details")
        info_layout = QVBoxLayout(info_group)
        self.info_id = QLabel("ID: -")
        self.info_type = QLabel("Type: -")
        self.info_dim = QLabel("Dimensions: -")
        self.info_sim = QLabel("Similarity: -")
        for label in [self.info_id, self.info_type, self.info_dim, self.info_sim]:
            info_layout.addWidget(label)
        right_layout.addWidget(info_group)

        splitter.addWidget(right_widget)
        splitter.setSizes([600, 300])
        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def init_gallery_dialog(self):
        result = init_gallery(str(self.gallery_path))
        if result.success:
            QMessageBox.information(self, "Success", "Gallery initialized successfully")
            self.refresh_gallery()
        else:
            QMessageBox.warning(self, "Error", result.error or "Unknown error")

    def add_images_dialog(self):
        if not self.core.is_initialized():
            QMessageBox.warning(
                self, "Warning", "Gallery not initialized. Click 'Init Gallery' first."
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
                        self, "Error", f"Failed to add {Path(file_path).name}:\n{result.error}"
                    )
                self.progress.setValue(i + 1)
            self.progress.setVisible(False)
            self.refresh_gallery()

    def refresh_gallery(self):
        if not self.core.is_initialized():
            self.status_bar.showMessage("Not initialized")
            return
        result = list_images(str(self.gallery_path), limit=1000)
        if result.success:
            images = result.data.get("images", [])
            self.image_table.setRowCount(len(images))
            for row, img in enumerate(images):
                id_item = QTableWidgetItem(img["id"][:16])
                self.image_table.setItem(row, 0, id_item)
                type_item = QTableWidgetItem("Base" if img["is_base"] else "Delta")
                self.image_table.setItem(row, 1, type_item)
                self.image_table.setItem(
                    row, 2, QTableWidgetItem(f"{img['width']} × {img['height']}")
                )
                self.image_table.setItem(
                    row, 3, QTableWidgetItem(self._format_size(img["file_size"]))
                )
                sim = img.get("similarity_score", 1.0) if not img["is_base"] else 1.0
                self.image_table.setItem(row, 4, QTableWidgetItem(f"{sim:.1%}"))
        stats_result = get_gallery_stats(str(self.gallery_path))
        if stats_result.success:
            stats = stats_result.data
            self.stat_labels["Total"].setText(str(stats["total_images"]))
            self.stat_labels["Base"].setText(str(stats["base_images"]))
            self.stat_labels["Delta"].setText(str(stats["delta_images"]))
            self.stat_labels["Saved"].setText(f"{stats['savings_ratio']:.1%}")
            self.status_bar.showMessage(
                f"Total: {self._format_size(stats['total_size'])} | Saved: {stats['savings_ratio']:.1%}"
            )

    def on_selection_changed(self):
        selected = self.image_table.selectedItems()
        if not selected:
            self.clear_preview()
            return
        row = selected[0].row()
        id_item = self.image_table.item(row, 0)
        if id_item:
            self.show_image_preview(id_item.text())

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
            scaled = pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
            self.info_id.setText(f"ID: {image_id[:16]}...")
            self.info_type.setText(f"Type: {'Base' if record['is_base'] else 'Delta'}")
            self.info_dim.setText(f"Dimensions: {record['width']} × {record['height']}")
            sim = record.get("similarity_score", 1.0) if not record["is_base"] else 1.0
            self.info_sim.setText(f"Similarity: {sim:.1%}")
        else:
            self.clear_preview()

    def clear_preview(self):
        self.image_label.clear()
        self.image_label.setText("Select an image")
        self.info_id.setText("ID: -")
        self.info_type.setText("Type: -")
        self.info_dim.setText("Dimensions: -")
        self.info_sim.setText("Similarity: -")

    def export_selected(self):
        selected = self.image_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Warning", "No image selected")
            return
        row = selected[0].row()
        id_item = self.image_table.item(row, 0)
        if not id_item:
            return
        image_id = id_item.text()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Image", f"{image_id}.png", "PNG (*.png);;JPEG (*.jpg)"
        )
        if file_path:
            result = export_image(image_id, file_path, str(self.gallery_path))
            if result.success:
                QMessageBox.information(self, "Success", f"Exported to {file_path}")
            else:
                QMessageBox.warning(self, "Error", result.error or "Export failed")

    def remove_selected(self):
        selected = self.image_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Warning", "No image selected")
            return
        row = selected[0].row()
        id_item = self.image_table.item(row, 0)
        if not id_item:
            return
        image_id = id_item.text()
        reply = QMessageBox.question(
            self, "Confirm", f"Remove image {image_id[:16]}...?", QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            result = remove_image(image_id, str(self.gallery_path))
            if result.success:
                self.refresh_gallery()
                self.clear_preview()
            else:
                QMessageBox.warning(self, "Error", result.error or "Remove failed")

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
    window = MainWindow(gallery_path)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
