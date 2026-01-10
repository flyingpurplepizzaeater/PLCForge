"""
PLCForge Main Window

PyQt6-based main application window with:
- Project explorer
- Code editor
- Device monitor
- AI assistant
- Password recovery wizard
"""

import sys
from typing import Optional, Dict, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QTextEdit, QTabWidget,
    QToolBar, QStatusBar, QMenuBar, QMenu, QFileDialog, QMessageBox,
    QDialog, QDialogButtonBox, QLabel, QLineEdit, QComboBox,
    QCheckBox, QProgressBar, QGroupBox, QFormLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDockWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont, QColor

from plcforge.pal.unified_api import DeviceFactory, UnifiedPLC, Vendor
from plcforge.drivers.base import PLCMode, DeviceInfo
from plcforge.recovery.engine import (
    RecoveryEngine, RecoveryTarget, RecoveryConfig,
    RecoveryMethod, RecoveryProgress, RecoveryResult, RecoveryStatus
)
from plcforge.security.audit_log import get_logger


class PLCForgeMainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PLCForge - Multi-Vendor PLC Programming")
        self.setMinimumSize(1200, 800)

        self._connected_devices: Dict[str, UnifiedPLC] = {}
        self._current_project: Optional[Path] = None
        self._audit_logger = get_logger()

        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_statusbar()

    def _setup_ui(self):
        """Set up main UI layout"""
        # Central widget with splitters
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        # Left panel - Project Explorer
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabel("Project Explorer")
        self.project_tree.setMinimumWidth(200)
        self._populate_project_tree()
        main_splitter.addWidget(self.project_tree)

        # Center panel - Code Editor and Monitor
        center_splitter = QSplitter(Qt.Orientation.Vertical)

        # Code editor tabs
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.tabCloseRequested.connect(self._close_editor_tab)

        # Add default welcome tab
        welcome = QTextEdit()
        welcome.setReadOnly(True)
        welcome.setHtml("""
        <h2>Welcome to PLCForge</h2>
        <p>Multi-vendor PLC programming with AI assistance.</p>
        <h3>Quick Start:</h3>
        <ul>
            <li><b>Connect to PLC:</b> PLC → Connect or Ctrl+K</li>
            <li><b>Open Project:</b> File → Open Project</li>
            <li><b>AI Code Generation:</b> AI → Generate Code</li>
            <li><b>Password Recovery:</b> Tools → Password Recovery</li>
        </ul>
        <h3>Supported Vendors:</h3>
        <ul>
            <li>Siemens S7-300/400/1200/1500</li>
            <li>Allen-Bradley CompactLogix/ControlLogix</li>
            <li>Delta DVP Series</li>
            <li>Omron CP/CJ/NX/NJ Series</li>
        </ul>
        """)
        self.editor_tabs.addTab(welcome, "Welcome")

        center_splitter.addWidget(self.editor_tabs)

        # Device monitor
        self.monitor_table = QTableWidget()
        self.monitor_table.setColumnCount(6)
        self.monitor_table.setHorizontalHeaderLabels([
            "Tag", "Value", "Type", "Address", "Forcing", "Trend"
        ])
        self.monitor_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.monitor_table.setMinimumHeight(150)
        center_splitter.addWidget(self.monitor_table)

        center_splitter.setSizes([500, 200])
        main_splitter.addWidget(center_splitter)

        # Right panel - AI Assistant (as dock)
        self._setup_ai_dock()

        main_splitter.setSizes([200, 800, 300])

    def _setup_ai_dock(self):
        """Set up AI assistant dock widget"""
        ai_dock = QDockWidget("AI Assistant", self)
        ai_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )

        ai_widget = QWidget()
        ai_layout = QVBoxLayout(ai_widget)

        # AI input
        self.ai_input = QTextEdit()
        self.ai_input.setPlaceholderText(
            "Describe what you want to create...\n"
            "Example: Create a conveyor control with 3 stations and emergency stop"
        )
        self.ai_input.setMaximumHeight(100)
        ai_layout.addWidget(self.ai_input)

        # AI controls
        ai_controls = QHBoxLayout()

        self.ai_vendor_combo = QComboBox()
        self.ai_vendor_combo.addItems([
            "Siemens", "Allen-Bradley", "Delta", "Omron", "Generic IEC"
        ])
        ai_controls.addWidget(QLabel("Vendor:"))
        ai_controls.addWidget(self.ai_vendor_combo)

        self.ai_language_combo = QComboBox()
        self.ai_language_combo.addItems([
            "Structured Text", "Ladder", "Function Block", "Instruction List"
        ])
        ai_controls.addWidget(QLabel("Language:"))
        ai_controls.addWidget(self.ai_language_combo)

        ai_layout.addLayout(ai_controls)

        # Generate button
        generate_btn = QPushButton("Generate Code")
        generate_btn.clicked.connect(self._generate_ai_code)
        ai_layout.addWidget(generate_btn)

        # AI output
        self.ai_output = QTextEdit()
        self.ai_output.setReadOnly(True)
        self.ai_output.setPlaceholderText("Generated code will appear here...")
        ai_layout.addWidget(self.ai_output)

        ai_dock.setWidget(ai_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, ai_dock)

    def _setup_menus(self):
        """Set up menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        # Standard edit actions would go here

        # View menu
        view_menu = menubar.addMenu("&View")

        # PLC menu
        plc_menu = menubar.addMenu("&PLC")

        connect_action = QAction("&Connect...", self)
        connect_action.setShortcut("Ctrl+K")
        connect_action.triggered.connect(self._connect_plc)
        plc_menu.addAction(connect_action)

        disconnect_action = QAction("&Disconnect", self)
        disconnect_action.triggered.connect(self._disconnect_plc)
        plc_menu.addAction(disconnect_action)

        plc_menu.addSeparator()

        upload_action = QAction("&Upload from PLC", self)
        upload_action.triggered.connect(self._upload_from_plc)
        plc_menu.addAction(upload_action)

        download_action = QAction("&Download to PLC", self)
        download_action.triggered.connect(self._download_to_plc)
        plc_menu.addAction(download_action)

        plc_menu.addSeparator()

        start_action = QAction("&Start PLC", self)
        start_action.triggered.connect(self._start_plc)
        plc_menu.addAction(start_action)

        stop_action = QAction("S&top PLC", self)
        stop_action.triggered.connect(self._stop_plc)
        plc_menu.addAction(stop_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        recovery_action = QAction("&Password Recovery...", self)
        recovery_action.triggered.connect(self._show_recovery_wizard)
        tools_menu.addAction(recovery_action)

        tools_menu.addSeparator()

        scan_action = QAction("&Network Scanner...", self)
        scan_action.triggered.connect(self._show_network_scanner)
        tools_menu.addAction(scan_action)

        # AI menu
        ai_menu = menubar.addMenu("&AI")

        generate_action = QAction("&Generate Code...", self)
        generate_action.setShortcut("Ctrl+G")
        generate_action.triggered.connect(self._generate_ai_code)
        ai_menu.addAction(generate_action)

        explain_action = QAction("&Explain Selected Code", self)
        explain_action.triggered.connect(self._explain_code)
        ai_menu.addAction(explain_action)

        optimize_action = QAction("&Optimize Code", self)
        optimize_action.triggered.connect(self._optimize_code)
        ai_menu.addAction(optimize_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About PLCForge", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """Set up main toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Connect button
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self._connect_plc)
        toolbar.addWidget(connect_btn)

        toolbar.addSeparator()

        # Upload/Download
        upload_btn = QPushButton("Upload")
        upload_btn.clicked.connect(self._upload_from_plc)
        toolbar.addWidget(upload_btn)

        download_btn = QPushButton("Download")
        download_btn.clicked.connect(self._download_to_plc)
        toolbar.addWidget(download_btn)

        toolbar.addSeparator()

        # Run/Stop
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self._start_plc)
        toolbar.addWidget(run_btn)

        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self._stop_plc)
        toolbar.addWidget(stop_btn)

        toolbar.addSeparator()

        # Password Recovery
        unlock_btn = QPushButton("Unlock")
        unlock_btn.clicked.connect(self._show_recovery_wizard)
        toolbar.addWidget(unlock_btn)

    def _setup_statusbar(self):
        """Set up status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        # Connection status
        self.connection_label = QLabel("Not Connected")
        self.statusbar.addWidget(self.connection_label)

        # Mode indicator
        self.mode_label = QLabel("")
        self.statusbar.addPermanentWidget(self.mode_label)

    def _populate_project_tree(self):
        """Populate project tree with structure"""
        self.project_tree.clear()

        # Root items for each vendor
        vendors = ["Siemens", "Allen-Bradley", "Delta", "Omron"]

        for vendor in vendors:
            vendor_item = QTreeWidgetItem([vendor])
            self.project_tree.addTopLevelItem(vendor_item)

    # Menu action handlers

    def _new_project(self):
        """Create new project"""
        # TODO: Implement new project dialog
        pass

    def _open_project(self):
        """Open existing project"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PLC Project",
            "",
            "All Supported (*.ap16 *.ap17 *.ap18 *.ap19 *.ap20 *.acd *.dvp *.cxp);;"
            "TIA Portal (*.ap13 *.ap14 *.ap15 *.ap16 *.ap17 *.ap18 *.ap19 *.ap20);;"
            "Studio 5000 (*.acd);;"
            "ISPSoft (*.dvp);;"
            "CX-Programmer (*.cxp);;"
            "All Files (*)"
        )

        if file_path:
            self._load_project(file_path)

    def _load_project(self, file_path: str):
        """Load a project file"""
        # TODO: Implement project loading
        self._current_project = Path(file_path)
        self.statusbar.showMessage(f"Loaded: {file_path}")

    def _save_project(self):
        """Save current project"""
        # TODO: Implement project saving
        pass

    def _connect_plc(self):
        """Show PLC connection dialog"""
        dialog = ConnectDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            ip = dialog.ip_input.text()
            vendor = dialog.vendor_combo.currentText().lower()

            try:
                # Map vendor names
                vendor_map = {
                    'siemens': 'siemens',
                    'allen-bradley': 'allen_bradley',
                    'delta': 'delta',
                    'omron': 'omron',
                }

                device = DeviceFactory.create(
                    ip,
                    vendor=vendor_map.get(vendor, vendor)
                )
                plc = UnifiedPLC(device)

                # Store connection
                self._connected_devices[ip] = plc

                # Update UI
                info = plc.info
                self.connection_label.setText(
                    f"Connected: {info.vendor} {info.model} @ {ip}"
                )
                self.mode_label.setText(f"Mode: {plc.mode.value.upper()}")

                # Log connection
                self._audit_logger.log_plc_connection(
                    ip, info.vendor, info.model, True
                )

                self.statusbar.showMessage(f"Connected to {ip}")

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Connection Failed",
                    f"Could not connect to PLC:\n{str(e)}"
                )

    def _disconnect_plc(self):
        """Disconnect from current PLC"""
        for ip, plc in list(self._connected_devices.items()):
            plc.disconnect()
            del self._connected_devices[ip]

        self.connection_label.setText("Not Connected")
        self.mode_label.setText("")
        self.statusbar.showMessage("Disconnected")

    def _upload_from_plc(self):
        """Upload program from connected PLC"""
        if not self._connected_devices:
            QMessageBox.warning(self, "Not Connected", "Please connect to a PLC first.")
            return

        # TODO: Implement upload
        self.statusbar.showMessage("Upload not yet implemented")

    def _download_to_plc(self):
        """Download program to connected PLC"""
        if not self._connected_devices:
            QMessageBox.warning(self, "Not Connected", "Please connect to a PLC first.")
            return

        # TODO: Implement download
        self.statusbar.showMessage("Download not yet implemented")

    def _start_plc(self):
        """Start connected PLC"""
        for plc in self._connected_devices.values():
            if plc.start():
                self.mode_label.setText("Mode: RUN")
                self.statusbar.showMessage("PLC started")
            else:
                QMessageBox.warning(self, "Start Failed", "Could not start PLC")

    def _stop_plc(self):
        """Stop connected PLC"""
        for plc in self._connected_devices.values():
            if plc.stop():
                self.mode_label.setText("Mode: STOP")
                self.statusbar.showMessage("PLC stopped")
            else:
                QMessageBox.warning(self, "Stop Failed", "Could not stop PLC")

    def _show_recovery_wizard(self):
        """Show password recovery wizard"""
        wizard = PasswordRecoveryWizard(self)
        wizard.exec()

    def _show_network_scanner(self):
        """Show network scanner dialog"""
        # TODO: Implement network scanner
        QMessageBox.information(
            self,
            "Network Scanner",
            "Network scanner not yet implemented"
        )

    def _generate_ai_code(self):
        """Generate code using AI"""
        prompt = self.ai_input.toPlainText()
        if not prompt:
            return

        self.ai_output.setText("Generating code...")

        # TODO: Connect to actual AI code generator
        # For now, show placeholder
        self.ai_output.setText("""
// Generated Structured Text
// Conveyor Control with Emergency Stop

VAR
    ConveyorRunning : BOOL := FALSE;
    EStop : BOOL := FALSE;
    StartButton : BOOL;
    StopButton : BOOL;
    Motor1 : BOOL;
END_VAR

// Emergency stop takes priority
IF EStop THEN
    ConveyorRunning := FALSE;
    Motor1 := FALSE;
    RETURN;
END_IF;

// Normal operation
IF StartButton AND NOT StopButton THEN
    ConveyorRunning := TRUE;
ELSIF StopButton THEN
    ConveyorRunning := FALSE;
END_IF;

Motor1 := ConveyorRunning;
        """)

    def _explain_code(self):
        """Explain selected code"""
        # TODO: Implement code explanation
        pass

    def _optimize_code(self):
        """Optimize current code"""
        # TODO: Implement code optimization
        pass

    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About PLCForge",
            """<h2>PLCForge v1.0</h2>
            <p>Multi-Vendor PLC Programming Application</p>
            <p>Supports: Siemens, Allen-Bradley, Delta, Omron</p>
            <p>Features:</p>
            <ul>
                <li>Multi-vendor PLC communication</li>
                <li>AI-assisted code generation</li>
                <li>Password recovery</li>
                <li>Project file management</li>
            </ul>
            <p><b>For authorized use only.</b></p>
            """
        )

    def _close_editor_tab(self, index: int):
        """Close an editor tab"""
        if index > 0:  # Don't close welcome tab
            self.editor_tabs.removeTab(index)


class ConnectDialog(QDialog):
    """PLC Connection dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to PLC")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Vendor selection
        vendor_layout = QHBoxLayout()
        vendor_layout.addWidget(QLabel("Vendor:"))
        self.vendor_combo = QComboBox()
        self.vendor_combo.addItems([
            "Siemens", "Allen-Bradley", "Delta", "Omron"
        ])
        vendor_layout.addWidget(self.vendor_combo)
        layout.addLayout(vendor_layout)

        # IP address
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("IP Address:"))
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.10")
        ip_layout.addWidget(self.ip_input)
        layout.addLayout(ip_layout)

        # Additional options
        options_group = QGroupBox("Options")
        options_layout = QFormLayout()

        self.rack_input = QLineEdit("0")
        options_layout.addRow("Rack:", self.rack_input)

        self.slot_input = QLineEdit("1")
        options_layout.addRow("Slot:", self.slot_input)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class PasswordRecoveryWizard(QDialog):
    """Password recovery wizard dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password Recovery Wizard")
        self.setMinimumSize(600, 500)

        self._engine = RecoveryEngine()
        self._audit_logger = get_logger()

        layout = QVBoxLayout(self)

        # Authorization section
        auth_group = QGroupBox("Step 1: Authorization")
        auth_layout = QVBoxLayout()

        auth_layout.addWidget(QLabel(
            "<b>Important:</b> Password recovery should only be performed on "
            "equipment you own or are authorized to access."
        ))

        self.auth_check1 = QCheckBox(
            "I confirm I am authorized to recover this password "
            "(equipment owner/authorized technician)"
        )
        auth_layout.addWidget(self.auth_check1)

        self.auth_check2 = QCheckBox(
            "I understand this action will be logged for security purposes"
        )
        auth_layout.addWidget(self.auth_check2)

        self.auth_check3 = QCheckBox(
            "I accept responsibility for this operation"
        )
        auth_layout.addWidget(self.auth_check3)

        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)

        # Target section
        target_group = QGroupBox("Step 2: Target Selection")
        target_layout = QFormLayout()

        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems(["Backup File", "Online PLC"])
        target_layout.addRow("Target Type:", self.target_type_combo)

        self.file_path_input = QLineEdit()
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_path_input)
        file_layout.addWidget(browse_btn)
        target_layout.addRow("File Path:", file_layout)

        self.vendor_combo = QComboBox()
        self.vendor_combo.addItems(["Siemens", "Allen-Bradley", "Delta", "Omron"])
        target_layout.addRow("Vendor:", self.vendor_combo)

        target_group.setLayout(target_layout)
        layout.addWidget(target_group)

        # Methods section
        methods_group = QGroupBox("Step 3: Recovery Methods")
        methods_layout = QVBoxLayout()

        self.method_file = QCheckBox("File Analysis (instant)")
        self.method_file.setChecked(True)
        methods_layout.addWidget(self.method_file)

        self.method_dict = QCheckBox("Dictionary Attack")
        self.method_dict.setChecked(True)
        methods_layout.addWidget(self.method_dict)

        self.method_vuln = QCheckBox("Known Vulnerabilities")
        methods_layout.addWidget(self.method_vuln)

        self.method_brute = QCheckBox("Brute Force (slow)")
        methods_layout.addWidget(self.method_brute)

        methods_group.setLayout(methods_layout)
        layout.addWidget(methods_group)

        # Progress section
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Result section
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(100)
        self.result_text.setVisible(False)
        layout.addWidget(self.result_text)

        # Buttons
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Recovery")
        self.start_btn.clicked.connect(self._start_recovery)
        button_layout.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel_recovery)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _browse_file(self):
        """Browse for project file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Project File",
            "",
            "All Supported (*.ap16 *.ap17 *.ap18 *.ap19 *.ap20 *.acd *.dvp *.cxp);;"
            "All Files (*)"
        )
        if file_path:
            self.file_path_input.setText(file_path)

    def _start_recovery(self):
        """Start password recovery"""
        # Check authorization
        if not (self.auth_check1.isChecked() and
                self.auth_check2.isChecked() and
                self.auth_check3.isChecked()):
            QMessageBox.warning(
                self,
                "Authorization Required",
                "Please acknowledge all authorization checkboxes before proceeding."
            )
            return

        # Log authorization
        self._audit_logger.log_authorization("password_recovery", True)

        # Build config
        methods = []
        if self.method_file.isChecked():
            methods.append(RecoveryMethod.FILE_PARSE)
        if self.method_dict.isChecked():
            methods.append(RecoveryMethod.DICTIONARY)
        if self.method_vuln.isChecked():
            methods.append(RecoveryMethod.VULNERABILITY)
        if self.method_brute.isChecked():
            methods.append(RecoveryMethod.BRUTEFORCE)

        if not methods:
            QMessageBox.warning(self, "No Methods", "Select at least one recovery method.")
            return

        config = RecoveryConfig(
            methods=methods,
            callback=self._update_progress
        )

        # Build target
        vendor_map = {
            "Siemens": "siemens",
            "Allen-Bradley": "allen_bradley",
            "Delta": "delta",
            "Omron": "omron",
        }

        target = RecoveryTarget(
            target_type="backup_file" if self.target_type_combo.currentIndex() == 0 else "online_plc",
            vendor=vendor_map[self.vendor_combo.currentText()],
            model="",
            protection_type="project",
            file_path=self.file_path_input.text() if self.target_type_combo.currentIndex() == 0 else None,
        )

        # Update UI
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.status_label.setText("Starting recovery...")

        # Run recovery (in real app, this would be in a thread)
        import time
        start_time = time.time()

        result = self._engine.recover(target, config, authorization_confirmed=True)

        duration_ms = int((time.time() - start_time) * 1000)

        # Log result
        self._audit_logger.log_password_recovery(
            target.target_type,
            target.file_path or "",
            target.vendor,
            result.method_used.value if result.method_used else "none",
            result.status == RecoveryStatus.SUCCESS,
            duration_ms,
            password_hash=None  # Don't log actual password
        )

        # Show result
        self.progress_bar.setVisible(False)
        self.result_text.setVisible(True)
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        if result.status == RecoveryStatus.SUCCESS:
            self.status_label.setText("Recovery successful!")
            self.result_text.setHtml(f"""
                <p><b>Password recovered!</b></p>
                <p>Method used: {result.method_used.value if result.method_used else 'N/A'}</p>
                <p>Attempts: {result.attempts}</p>
                <p>Password: <code>{result.password}</code></p>
            """)
        else:
            self.status_label.setText("Recovery failed")
            self.result_text.setHtml(f"""
                <p><b>Recovery unsuccessful</b></p>
                <p>Reason: {result.error_message or 'Unknown'}</p>
                <p>Attempts: {result.attempts}</p>
            """)

    def _cancel_recovery(self):
        """Cancel ongoing recovery"""
        self._engine.cancel()
        self.status_label.setText("Cancelled")
        self.progress_bar.setVisible(False)
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def _update_progress(self, progress: RecoveryProgress):
        """Update progress display"""
        self.status_label.setText(
            f"Method: {progress.method.value} | "
            f"Attempts: {progress.attempts:,} | "
            f"Rate: {progress.rate_per_second:.0f}/s"
        )


def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("PLCForge")
    app.setOrganizationName("PLCForge")

    # Set application style
    app.setStyle("Fusion")

    window = PLCForgeMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
