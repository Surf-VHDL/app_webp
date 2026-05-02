#!/usr/bin/env python3
"""app_webp - Desktop converter JPG/PNG -> WebP via cwebp."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_ORG = "app_webp"
APP_NAME = "app_webp"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


@dataclass
class ConversionTask:
    source_path: Path
    output_path: Path


class ConversionWorker(QObject):
    progress = Signal(int, int)
    log = Signal(str, str)
    finished = Signal(int, int, int)

    def __init__(self, tasks: list[ConversionTask], quality: int, cwebp_path: str) -> None:
        super().__init__()
        self.tasks = tasks
        self.quality = quality
        self.cwebp_path = cwebp_path

    @Slot()
    def run(self) -> None:
        converted = 0
        failed = 0
        skipped = 0
        total = len(self.tasks)

        for index, task in enumerate(self.tasks, start=1):
            cmd = [
                self.cwebp_path,
                "-q",
                str(self.quality),
                str(task.source_path),
                "-o",
                str(task.output_path),
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    shell=False,
                )
                if result.returncode == 0:
                    converted += 1
                    self.log.emit(
                        "INFO",
                        f"Convertito: {task.source_path.name} -> {task.output_path.name}",
                    )
                else:
                    failed += 1
                    details = result.stderr.strip() or result.stdout.strip() or "Errore sconosciuto"
                    self.log.emit(
                        "ERROR",
                        f"Fallito: {task.source_path.name} ({details})",
                    )
            except Exception as exc:  # pragma: no cover - runtime guard
                failed += 1
                self.log.emit("ERROR", f"Eccezione su {task.source_path.name}: {exc}")

            self.progress.emit(index, total)

        self.finished.emit(converted, failed, skipped)


class DropZone(QFrame):
    files_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropZone")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Trascina qui le immagini")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 600;")

        subtitle = QLabel("Supporta JPG, JPEG, PNG. Rilascio multiplo.")
        subtitle.setAlignment(Qt.AlignCenter)

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)

        self._default_style = (
            "QFrame#dropZone {"
            "border: 2px dashed #4b5563;"
            "border-radius: 12px;"
            "background: #111827;"
            "color: #f9fafb;"
            "}"
        )
        self._active_style = (
            "QFrame#dropZone {"
            "border: 2px dashed #22c55e;"
            "border-radius: 12px;"
            "background: #1f2937;"
            "color: #f9fafb;"
            "}"
        )
        self.setStyleSheet(self._default_style)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if any(self._is_supported_url(url.toLocalFile()) for url in urls):
            event.acceptProposedAction()
            self.setStyleSheet(self._active_style)
            return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet(self._default_style)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self.setStyleSheet(self._default_style)
        dropped = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if self._is_supported_url(path):
                dropped.append(path)

        if dropped:
            self.files_dropped.emit(dropped)
            event.acceptProposedAction()
        else:
            event.ignore()

    @staticmethod
    def _is_supported_url(path_str: str) -> bool:
        if not path_str:
            return False
        path = Path(path_str)
        return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("app_webp")
        self.resize(980, 760)

        self.settings = QSettings(APP_ORG, APP_NAME)
        self.input_files: list[Path] = []
        self.worker_thread: QThread | None = None
        self.worker: ConversionWorker | None = None
        self.cwebp_path = ""
        self._pre_skipped_count = 0

        self._build_ui()
        self._load_settings()
        QTimer.singleShot(0, self._startup_check_cwebp)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        self.drop_zone = DropZone()
        self.drop_zone.setMinimumHeight(220)
        self.drop_zone.files_dropped.connect(self._add_files)

        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(140)

        list_actions = QHBoxLayout()
        self.pick_button = QPushButton("Seleziona file")
        self.clear_button = QPushButton("Pulisci lista")
        self.count_label = QLabel("0 file in coda")
        list_actions.addWidget(self.pick_button)
        list_actions.addWidget(self.clear_button)
        list_actions.addStretch(1)
        list_actions.addWidget(self.count_label)

        self.pick_button.clicked.connect(self._pick_files)
        self.clear_button.clicked.connect(self._clear_files)

        controls = QGroupBox("Parametri conversione")
        controls_grid = QGridLayout(controls)

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(0, 100)
        self.quality_slider.setValue(80)
        self.quality_label = QLabel("80")
        self.quality_slider.valueChanged.connect(
            lambda value: self.quality_label.setText(str(value))
        )

        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("Prefisso opzionale")

        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("Suffisso opzionale")

        self.output_input = QLineEdit()
        self.output_input.setReadOnly(True)
        self.output_input.setPlaceholderText("Se vuoto: stessa cartella del file originale")

        self.browse_output_button = QPushButton("Seleziona cartella output")
        self.clear_output_button = QPushButton("Reset output")
        self.start_button = QPushButton("Avvia conversione")

        self.browse_output_button.clicked.connect(self._pick_output_dir)
        self.clear_output_button.clicked.connect(lambda: self.output_input.setText(""))
        self.start_button.clicked.connect(self._start_conversion)

        controls_grid.addWidget(QLabel("Qualita"), 0, 0)
        controls_grid.addWidget(self.quality_slider, 0, 1)
        controls_grid.addWidget(self.quality_label, 0, 2)
        controls_grid.addWidget(QLabel("Prefisso"), 1, 0)
        controls_grid.addWidget(self.prefix_input, 1, 1, 1, 2)
        controls_grid.addWidget(QLabel("Suffisso"), 2, 0)
        controls_grid.addWidget(self.suffix_input, 2, 1, 1, 2)
        controls_grid.addWidget(self.browse_output_button, 3, 0)
        controls_grid.addWidget(self.clear_output_button, 3, 1)
        controls_grid.addWidget(self.output_input, 4, 0, 1, 3)
        controls_grid.addWidget(self.start_button, 5, 0, 1, 3)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMinimumHeight(180)
        self.log_console.setStyleSheet(
            "background: #000000; color: #22c55e; font-family: Menlo, Monaco, monospace;"
        )

        layout.addWidget(self.drop_zone)
        layout.addLayout(list_actions)
        layout.addWidget(self.file_list)
        layout.addWidget(controls)
        layout.addWidget(self.progress)
        layout.addWidget(self.log_console)

    def _load_settings(self) -> None:
        quality = int(self.settings.value("quality", 80))
        self.quality_slider.setValue(max(0, min(100, quality)))
        self.prefix_input.setText(self.settings.value("prefix", ""))
        self.suffix_input.setText(self.settings.value("suffix", ""))
        self.output_input.setText(self.settings.value("output_dir", ""))

    def _save_settings(self) -> None:
        self.settings.setValue("quality", self.quality_slider.value())
        self.settings.setValue("prefix", self.prefix_input.text())
        self.settings.setValue("suffix", self.suffix_input.text())
        self.settings.setValue("output_dir", self.output_input.text())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._save_settings()
        super().closeEvent(event)

    def _startup_check_cwebp(self) -> None:
        if not self._check_cwebp(show_popup=True):
            self._log("ERROR", "Installa cwebp con: brew install webp")

    def _check_cwebp(self, show_popup: bool) -> bool:
        path = shutil.which("cwebp")
        if path:
            self.cwebp_path = path
            return True

        if show_popup:
            QMessageBox.critical(
                self,
                "cwebp non trovato",
                "Il comando cwebp non e disponibile.\n"
                "Installa il pacchetto con: brew install webp",
            )
        return False

    def _log(self, level: str, message: str) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"[{now}] {level:<5} {message}")
        self.log_console.verticalScrollBar().setValue(
            self.log_console.verticalScrollBar().maximum()
        )

    def _pick_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleziona immagini",
            "",
            "Immagini (*.jpg *.jpeg *.png)",
        )
        if files:
            self._add_files(files)

    def _clear_files(self) -> None:
        self.input_files.clear()
        self.file_list.clear()
        self._refresh_counter()
        self._log("INFO", "Lista input pulita")

    def _pick_output_dir(self) -> None:
        start_dir = self.output_input.text() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(
            self,
            "Seleziona cartella output",
            start_dir,
        )
        if selected:
            self.output_input.setText(selected)
            self._log("INFO", f"Output selezionato: {selected}")

    @Slot(list)
    def _add_files(self, paths: list[str]) -> None:
        existing = {p.resolve() for p in self.input_files}
        added = 0

        for item in paths:
            path = Path(item).expanduser().resolve()
            if not path.exists() or not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if path in existing:
                continue
            self.input_files.append(path)
            self.file_list.addItem(str(path))
            existing.add(path)
            added += 1

        if added:
            self._log("INFO", f"Aggiunti {added} file")
        else:
            self._log("INFO", "Nessun nuovo file aggiunto")
        self._refresh_counter()

    def _refresh_counter(self) -> None:
        self.count_label.setText(f"{len(self.input_files)} file in coda")

    def _start_conversion(self) -> None:
        if not self.input_files:
            QMessageBox.warning(self, "Nessun file", "Aggiungi almeno un file da convertire.")
            return

        if not self._check_cwebp(show_popup=True):
            self._log("ERROR", "Conversione bloccata: cwebp non disponibile")
            return

        quality = self.quality_slider.value()
        output_base = Path(self.output_input.text()).expanduser() if self.output_input.text() else None
        prefix = self.prefix_input.text().strip()
        suffix = self.suffix_input.text().strip()

        overwrite_all: bool | None = None
        tasks: list[ConversionTask] = []
        skipped_existing = 0

        for source_path in self.input_files:
            target_dir = output_base if output_base else source_path.parent
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                skipped_existing += 1
                self._log("ERROR", f"Output non accessibile per {source_path.name}: {exc}")
                continue

            output_name = build_output_name(source_path, prefix, suffix)
            output_path = target_dir / output_name

            if output_path.exists():
                decision, overwrite_all = self._ask_overwrite(output_path, overwrite_all)
                if decision == "cancel":
                    self._log("INFO", "Conversione annullata dall'utente")
                    return
                if decision == "skip":
                    skipped_existing += 1
                    self._log("INFO", f"Saltato (esiste): {output_path.name}")
                    continue

            tasks.append(ConversionTask(source_path=source_path, output_path=output_path))

        if not tasks:
            self._log("INFO", "Nessun file da convertire dopo i controlli")
            return

        self.progress.setRange(0, len(tasks))
        self.progress.setValue(0)
        self._pre_skipped_count = skipped_existing
        self._set_controls_enabled(False)
        self._save_settings()

        self.worker_thread = QThread(self)
        self.worker = ConversionWorker(tasks=tasks, quality=quality, cwebp_path=self.cwebp_path)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log.connect(self._log)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.finished.connect(self._on_worker_finished)

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self._log(
            "INFO",
            f"Batch avviato: {len(tasks)} conversioni (saltati per conflitto: {skipped_existing})",
        )
        self.worker_thread.start()

    def _ask_overwrite(self, output_path: Path, overwrite_all: bool | None) -> tuple[str, bool | None]:
        if overwrite_all is True:
            return "overwrite", True
        if overwrite_all is False:
            return "skip", False

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("File gia presente")
        box.setText(
            f"Il file esiste gia:\n{output_path}\n\nVuoi sovrascriverlo?"
        )
        box.setStandardButtons(
            QMessageBox.Yes
            | QMessageBox.No
            | QMessageBox.YesToAll
            | QMessageBox.NoToAll
            | QMessageBox.Cancel
        )
        box.setDefaultButton(QMessageBox.Yes)

        choice = box.exec()
        if choice == QMessageBox.Yes:
            return "overwrite", None
        if choice == QMessageBox.No:
            return "skip", None
        if choice == QMessageBox.YesToAll:
            return "overwrite", True
        if choice == QMessageBox.NoToAll:
            return "skip", False
        return "cancel", None

    @Slot(int, int)
    def _on_worker_progress(self, done: int, total: int) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(done)

    @Slot(int, int, int)
    def _on_worker_finished(self, converted: int, failed: int, skipped_worker: int) -> None:
        self._set_controls_enabled(True)
        skipped_total = skipped_worker + self._pre_skipped_count
        self._log(
            "INFO",
            f"Batch terminato. Convertiti: {converted}, Falliti: {failed}, Saltati: {skipped_total}",
        )

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.drop_zone.setEnabled(enabled)
        self.pick_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
        self.browse_output_button.setEnabled(enabled)
        self.clear_output_button.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        self.prefix_input.setEnabled(enabled)
        self.suffix_input.setEnabled(enabled)
        self.quality_slider.setEnabled(enabled)


def to_kebab_case(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    collapsed = re.sub(r"-+", "-", cleaned)
    return collapsed.strip("-")


def build_output_name(source_path: Path, prefix: str, suffix: str) -> str:
    source_clean = to_kebab_case(source_path.stem) or "image"
    prefix_clean = to_kebab_case(prefix)
    suffix_clean = to_kebab_case(suffix)

    chunks = []
    if prefix_clean:
        chunks.append(prefix_clean)
    chunks.append(source_clean)
    if suffix_clean:
        chunks.append(suffix_clean)

    return f"{'-'.join(chunks)}.webp"


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
