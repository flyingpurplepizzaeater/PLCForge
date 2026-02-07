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
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from plcforge.gui.themes import Theme, ThemeManager
from plcforge.pal.unified_api import DeviceFactory, UnifiedPLC
from plcforge.recovery.engine import (
    RecoveryConfig,
    RecoveryEngine,
    RecoveryMethod,
    RecoveryProgress,
    RecoveryStatus,
    RecoveryTarget,
)
from plcforge.security.audit_log import get_logger


class PLCForgeMainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PLCForge - Multi-Vendor PLC Programming")
        self.setMinimumSize(1200, 800)

        self._connected_devices: dict[str, UnifiedPLC] = {}
        self._current_project: Path | None = None
        self._audit_logger = get_logger()
        self._theme_manager = ThemeManager(QApplication.instance())
        self._highlighters = {}

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
            <li>Mitsubishi MELSEC-Q/L/iQ-R/iQ-F Series</li>
            <li>Beckhoff TwinCAT 2/3</li>
            <li>Schneider Modicon M340/M580/Premium/Quantum</li>
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
        menubar.addMenu("&Edit")
        # Standard edit actions would go here

        # View menu
        view_menu = menubar.addMenu("&View")

        # Theme toggle
        self.dark_mode_action = QAction("&Dark Mode", self)
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.setShortcut("Ctrl+Shift+D")
        self.dark_mode_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(self.dark_mode_action)

        view_menu.addSeparator()

        # Syntax highlighting submenu
        syntax_menu = view_menu.addMenu("Syntax &Highlighting")

        st_action = QAction("Structured Text", self)
        st_action.triggered.connect(lambda: self._set_syntax("structured_text"))
        syntax_menu.addAction(st_action)

        ladder_action = QAction("Ladder", self)
        ladder_action.triggered.connect(lambda: self._set_syntax("ladder"))
        syntax_menu.addAction(ladder_action)

        il_action = QAction("Instruction List", self)
        il_action.triggered.connect(lambda: self._set_syntax("instruction_list"))
        syntax_menu.addAction(il_action)

        fbd_action = QAction("Function Block", self)
        fbd_action.triggered.connect(lambda: self._set_syntax("function_block"))
        syntax_menu.addAction(fbd_action)

        view_menu.addSeparator()

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
        vendors = ["Siemens", "Allen-Bradley", "Delta", "Omron", "Mitsubishi", "Beckhoff", "Schneider"]

        for vendor in vendors:
            vendor_item = QTreeWidgetItem([vendor])
            self.project_tree.addTopLevelItem(vendor_item)

    # Menu action handlers

    def _new_project(self):
        """Create new project"""
        dialog = NewProjectDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            project_name = dialog.name_input.text()
            project_path = dialog.path_input.text()
            vendor = dialog.vendor_combo.currentText().lower()

            # Create project directory
            full_path = Path(project_path) / project_name
            try:
                full_path.mkdir(parents=True, exist_ok=True)
                (full_path / "src").mkdir(exist_ok=True)
                (full_path / "backup").mkdir(exist_ok=True)

                # Create project metadata file
                import json
                project_info = {
                    "name": project_name,
                    "vendor": vendor,
                    "created": str(datetime.now()),
                    "version": "1.0.0"
                }
                with open(full_path / "project.json", "w") as f:
                    json.dump(project_info, f, indent=2)

                self._current_project = full_path
                self.statusbar.showMessage(f"Created project: {project_name}")
                self._populate_project_tree()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create project: {e}")

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
        try:
            file_path_obj = Path(file_path)

            # Check if it's a project directory or file
            if file_path_obj.is_dir():
                project_dir = file_path_obj
            elif file_path_obj.suffix == '.json':
                project_dir = file_path_obj.parent
            else:
                # It's a PLC project file - parse it
                self._parse_plc_project_file(file_path)
                return

            # Load project metadata
            project_file = project_dir / "project.json"
            if project_file.exists():
                import json
                with open(project_file) as f:
                    project_info = json.load(f)
                self._current_project = project_dir
                self.statusbar.showMessage(f"Loaded: {project_info.get('name', project_dir.name)}")
                self._populate_project_tree()
            else:
                self._current_project = file_path_obj
                self.statusbar.showMessage(f"Loaded: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load project: {e}")

    def _parse_plc_project_file(self, file_path: str):
        """Parse vendor-specific PLC project files"""
        file_path_obj = Path(file_path)
        suffix = file_path_obj.suffix.lower()

        try:
            if suffix in ['.ap13', '.ap14', '.ap15', '.ap16', '.ap17', '.ap18', '.ap19', '.ap20']:
                # TIA Portal project
                from plcforge.drivers.siemens.project_parser import TIAProjectParser
                parser = TIAProjectParser()
                program = parser.parse(file_path)
                self.code_editor.setText(f"# TIA Portal Project\n# Vendor: {program.vendor}\n# Model: {program.model}\n# Blocks: {len(program.blocks)}")
                self.statusbar.showMessage(f"Parsed TIA Portal project: {file_path_obj.name}")
            elif suffix == '.acd':
                # Studio 5000 project
                self.code_editor.setText("# Studio 5000 project loaded\n# Full parsing requires Studio 5000 SDK")
                self.statusbar.showMessage(f"Opened Studio 5000 project: {file_path_obj.name}")
            else:
                self.code_editor.setText(f"# Loaded: {file_path_obj.name}\n# Vendor-specific parsing not yet implemented")
                self.statusbar.showMessage(f"Opened: {file_path_obj.name}")
        except Exception as e:
            QMessageBox.warning(self, "Parse Error", f"Could not fully parse project: {e}")

    def _save_project(self):
        """Save current project"""
        if not self._current_project:
            QMessageBox.warning(self, "No Project", "No project is currently open.")
            return

        try:
            # Save current editor content
            code_file = self._current_project / "src" / "main.st"
            code_file.parent.mkdir(parents=True, exist_ok=True)
            with open(code_file, "w") as f:
                f.write(self.code_editor.toPlainText())

            # Update project metadata
            project_file = self._current_project / "project.json"
            if project_file.exists():
                import json
                with open(project_file) as f:
                    project_info = json.load(f)
                project_info["modified"] = str(datetime.now())
                with open(project_file, "w") as f:
                    json.dump(project_info, f, indent=2)

            self.statusbar.showMessage(f"Saved project: {self._current_project.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project: {e}")

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
                    'mitsubishi': 'mitsubishi',
                    'beckhoff': 'beckhoff',
                    'schneider': 'schneider',
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

        try:
            # Get the first connected device
            plc = list(self._connected_devices.values())[0]

            # Show progress dialog
            progress = QMessageBox(self)
            progress.setWindowTitle("Upload Program")
            progress.setText("Uploading program from PLC...")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.show()
            QApplication.processEvents()

            # Upload program
            program = plc.upload_program()

            # Display in editor
            editor_text = f"# Uploaded from {plc.info.vendor} {plc.info.model}\n"
            editor_text += f"# Firmware: {plc.info.firmware}\n\n"

            if program.blocks:
                editor_text += f"# Program Blocks ({len(program.blocks)})\n"
                for block in program.blocks[:10]:  # Show first 10 blocks
                    editor_text += f"# - {block.info.name} ({block.info.block_type.value})\n"

            if program.tags:
                editor_text += f"\n# Tags ({len(program.tags)})\n"
                for tag in program.tags[:20]:  # Show first 20 tags
                    editor_text += f"# - {tag.name}: {tag.data_type} = {tag.value}\n"

            self.code_editor.setText(editor_text)

            progress.close()
            self.statusbar.showMessage(f"Uploaded {len(program.blocks)} blocks, {len(program.tags)} tags")

        except Exception as e:
            QMessageBox.critical(self, "Upload Failed", f"Failed to upload program: {e}")
            self.statusbar.showMessage("Upload failed")

    def _download_to_plc(self):
        """Download program to connected PLC"""
        if not self._connected_devices:
            QMessageBox.warning(self, "Not Connected", "Please connect to a PLC first.")
            return

        # Confirm download
        reply = QMessageBox.question(
            self,
            "Confirm Download",
            "This will overwrite the PLC program. Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            plc = list(self._connected_devices.values())[0]

            # Create a minimal program structure
            from plcforge.drivers.base import PLCProgram
            program = PLCProgram(
                vendor=plc.info.vendor,
                model=plc.info.model
            )

            # Show progress
            progress = QMessageBox(self)
            progress.setWindowTitle("Download Program")
            progress.setText("Downloading program to PLC...")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.show()
            QApplication.processEvents()

            # Attempt download
            success = plc.download_program(program)

            progress.close()

            if success:
                QMessageBox.information(self, "Success", "Program downloaded successfully")
                self.statusbar.showMessage("Download successful")
            else:
                QMessageBox.warning(
                    self,
                    "Download Limited",
                    f"Full program download requires vendor software.\n"
                    f"Last error: {plc.last_error or 'Unknown'}"
                )
                self.statusbar.showMessage("Download not fully supported")

        except Exception as e:
            QMessageBox.critical(self, "Download Failed", f"Failed to download program: {e}")
            self.statusbar.showMessage("Download failed")

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
        dialog = NetworkScannerDialog(self)
        dialog.exec()

    def _generate_ai_code(self):
        """Generate code using AI"""
        prompt = self.ai_input.toPlainText()
        if not prompt:
            return

        self.ai_output.setText("Generating code...")
        QApplication.processEvents()

        try:
            # Try to use AI code generator if API keys are available
            import os

            from plcforge.ai.code_generator import AICodeGenerator, CodeTarget
            from plcforge.drivers.base import CodeLanguage, Vendor

            # Check for API keys
            openai_key = os.getenv('OPENAI_API_KEY')
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')

            if openai_key or anthropic_key:
                # Use real AI generation
                provider = "openai" if openai_key else "anthropic"
                api_key = openai_key or anthropic_key

                generator = AICodeGenerator(provider=provider, api_key=api_key)

                # Determine target based on connected PLC or default to Siemens
                if self._connected_devices:
                    plc = list(self._connected_devices.values())[0]
                    vendor_str = plc.info.vendor.upper()
                    vendor = Vendor[vendor_str] if vendor_str in Vendor.__members__ else Vendor.SIEMENS
                    model = plc.info.model
                else:
                    vendor = Vendor.SIEMENS
                    model = "S7-1500"

                target = CodeTarget(
                    vendor=vendor,
                    model=model,
                    language=CodeLanguage.STRUCTURED_TEXT
                )

                result = generator.generate(
                    prompt=prompt,
                    target=target,
                    safety_check=True
                )

                output = result.code
                if result.explanation:
                    output += f"\n\n// Explanation:\n// {result.explanation}"
                if result.safety_issues:
                    output += "\n\n// SAFETY WARNINGS:\n"
                    for issue in result.safety_issues:
                        output += f"// - {issue}\n"

                self.ai_output.setText(output)
                self.statusbar.showMessage("Code generated successfully")
            else:
                # Fallback to template-based generation
                self._generate_template_code(prompt)

        except Exception:
            # Fallback to template
            self._generate_template_code(prompt)
            self.statusbar.showMessage("Using template code (AI unavailable)")

    def _generate_template_code(self, prompt: str):
        """Generate template code when AI is unavailable"""
        prompt_lower = prompt.lower()

        # Simple keyword matching for common patterns
        if "motor" in prompt_lower or "conveyor" in prompt_lower:
            code = """
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
"""
        elif "timer" in prompt_lower or "delay" in prompt_lower:
            code = """
// Timer Example

VAR
    MyTimer : TON;
    StartTimer : BOOL;
    TimerRunning : BOOL;
    TimerDone : BOOL;
    Delay : TIME := T#5s;
END_VAR

MyTimer(IN := StartTimer, PT := Delay);
TimerRunning := MyTimer.Q;
TimerDone := MyTimer.Q;
"""
        elif "counter" in prompt_lower:
            code = """
// Counter Example

VAR
    MyCounter : CTU;
    CountInput : BOOL;
    ResetCounter : BOOL;
    CountValue : INT;
    MaxCount : INT := 100;
END_VAR

MyCounter(CU := CountInput, RESET := ResetCounter, PV := MaxCount);
CountValue := MyCounter.CV;
"""
        else:
            code = """
// Generated Structured Text Template

VAR
    // Add your variables here
END_VAR

// Add your code here
// Use standard IEC 61131-3 syntax

// Note: Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment
// variable to enable AI-powered code generation
"""

        self.ai_output.setText(code)

    def _explain_code(self):
        """Explain selected code"""
        code = self.code_editor.textCursor().selectedText()
        if not code:
            code = self.code_editor.toPlainText()

        if not code or not code.strip():
            QMessageBox.information(self, "No Code", "No code to explain. Please write or select some code.")
            return

        try:
            import os

            from plcforge.ai.code_generator import AICodeGenerator

            # Check for API keys
            openai_key = os.getenv('OPENAI_API_KEY')
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')

            if openai_key or anthropic_key:
                provider = "openai" if openai_key else "anthropic"
                api_key = openai_key or anthropic_key

                AICodeGenerator(provider=provider, api_key=api_key)

                # Generate explanation using the LLM directly

                # Simple explanation - we'd call the LLM here
                explanation = "Code Explanation:\n\n"
                explanation += "This code implements PLC logic using IEC 61131-3 standard.\n\n"
                explanation += "Key elements:\n"
                explanation += "- Variables are declared in VAR...END_VAR blocks\n"
                explanation += "- Logic uses IF/THEN/ELSE control structures\n"
                explanation += "- Boolean operations control outputs\n\n"
                explanation += "For detailed AI-powered explanations, the OpenAI/Anthropic API must be configured."

                QMessageBox.information(self, "Code Explanation", explanation)
            else:
                # Basic static explanation
                QMessageBox.information(
                    self,
                    "Code Explanation",
                    "Code explanation requires OpenAI or Anthropic API keys.\n\n"
                    "Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.\n\n"
                    "Selected code:\n" + code[:200] + ("..." if len(code) > 200 else "")
                )

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to explain code: {e}")

    def _optimize_code(self):
        """Optimize current code"""
        code = self.code_editor.toPlainText()
        if not code or not code.strip():
            QMessageBox.information(self, "No Code", "No code to optimize.")
            return

        try:
            import os

            # Check for API keys
            openai_key = os.getenv('OPENAI_API_KEY')
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')

            if openai_key or anthropic_key:
                reply = QMessageBox.question(
                    self,
                    "Optimize Code",
                    "This will replace your current code with an optimized version.\n\n"
                    "Do you want to continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply != QMessageBox.StandardButton.Yes:
                    return

                # Show progress
                progress = QMessageBox(self)
                progress.setWindowTitle("Optimizing Code")
                progress.setText("Optimizing your PLC code...")
                progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
                progress.show()
                QApplication.processEvents()

                # Here we would call AI to optimize
                # For now, show message
                progress.close()

                QMessageBox.information(
                    self,
                    "Code Optimization",
                    "Code optimization with AI is available but requires full API integration.\n\n"
                    "The code would be analyzed for:\n"
                    "- Unnecessary operations\n"
                    "- Redundant logic\n"
                    "- Performance improvements\n"
                    "- Safety enhancements"
                )
            else:
                QMessageBox.information(
                    self,
                    "Code Optimization",
                    "Code optimization requires OpenAI or Anthropic API keys.\n\n"
                    "Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable."
                )

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to optimize code: {e}")

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

    def _toggle_theme(self):
        """Toggle between light and dark themes"""
        new_theme = self._theme_manager.toggle_theme()
        self.dark_mode_action.setChecked(new_theme == Theme.DARK)
        # Update highlighters with new theme
        for highlighter in self._highlighters.values():
            if highlighter:
                highlighter.update_theme()

    def _set_syntax(self, language: str):
        """Set syntax highlighting for current editor"""
        from plcforge.gui.themes.syntax_highlighter import apply_highlighter
        current_widget = self.editor_tabs.currentWidget()
        if isinstance(current_widget, QTextEdit):
            # Remove old highlighter if exists
            tab_id = id(current_widget)
            if tab_id in self._highlighters:
                old = self._highlighters[tab_id]
                if old:
                    old.setDocument(None)
            # Apply new highlighter
            self._highlighters[tab_id] = apply_highlighter(current_widget, language)
            self.statusbar.showMessage(f"Syntax highlighting: {language.replace('_', ' ').title()}")


class NewProjectDialog(QDialog):
    """New Project dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Project name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Project Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("MyPLCProject")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Project path
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Location:"))
        self.path_input = QLineEdit()
        default_path = str(Path.home() / '.plcforge' / 'projects')
        self.path_input.setText(default_path)
        path_layout.addWidget(self.path_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        # Vendor selection
        vendor_layout = QHBoxLayout()
        vendor_layout.addWidget(QLabel("Target Vendor:"))
        self.vendor_combo = QComboBox()
        self.vendor_combo.addItems([
            "Siemens", "Allen-Bradley", "Delta", "Omron", "Mitsubishi", "Beckhoff", "Schneider"
        ])
        vendor_layout.addWidget(self.vendor_combo)
        layout.addLayout(vendor_layout)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_path(self):
        """Browse for project location"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Project Location",
            self.path_input.text()
        )
        if path:
            self.path_input.setText(path)

    def _validate_and_accept(self):
        """Validate inputs before accepting"""
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Invalid Input", "Please enter a project name.")
            return
        if not self.path_input.text().strip():
            QMessageBox.warning(self, "Invalid Input", "Please select a project location.")
            return
        self.accept()


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
            "Siemens", "Allen-Bradley", "Delta", "Omron", "Mitsubishi", "Beckhoff", "Schneider"
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


class NetworkScannerDialog(QDialog):
    """Network security scanner dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PLC Network Security Scanner")
        self.setMinimumSize(800, 600)

        from plcforge.security.network_scanner import (
            NetworkScanner,
        )
        self._scanner = NetworkScanner()
        self._scan_result = None

        layout = QVBoxLayout(self)

        # Scan configuration
        config_group = QGroupBox("Scan Configuration")
        config_layout = QFormLayout()

        self.subnet_input = QLineEdit()
        self.subnet_input.setPlaceholderText("192.168.1.0/24")
        self.subnet_input.setText("192.168.1.0/24")
        config_layout.addRow("Subnet (CIDR):", self.subnet_input)

        self.quick_scan_check = QCheckBox("Quick scan (common ports only)")
        self.quick_scan_check.setChecked(True)
        config_layout.addRow("", self.quick_scan_check)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Progress section
        progress_layout = QHBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to scan")
        progress_layout.addWidget(self.status_label)

        layout.addLayout(progress_layout)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "IP Address", "Hostname", "Vendor", "Model", "Open Ports", "Issues"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.results_table)

        # Issue details
        details_group = QGroupBox("Security Issues")
        details_layout = QVBoxLayout()

        self.issues_text = QTextEdit()
        self.issues_text.setReadOnly(True)
        self.issues_text.setMaximumHeight(150)
        details_layout.addWidget(self.issues_text)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.clicked.connect(self._start_scan)
        button_layout.addWidget(self.scan_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_scan)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)

        export_btn = QPushButton("Export Report")
        export_btn.clicked.connect(self._export_report)
        button_layout.addWidget(export_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # Connect table selection
        self.results_table.itemSelectionChanged.connect(self._show_device_issues)

    def _start_scan(self):
        """Start network scan"""
        subnet = self.subnet_input.text().strip()
        if not subnet:
            QMessageBox.warning(self, "Input Required", "Please enter a subnet to scan.")
            return

        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Scanning...")
        self.results_table.setRowCount(0)
        self.issues_text.clear()

        # Run scan in thread
        import threading
        def run_scan():
            from plcforge.security.network_scanner import NetworkScanner
            scanner = NetworkScanner()
            scanner.set_progress_callback(self._update_scan_progress)
            self._scan_result = scanner.scan_subnet(
                subnet,
                quick_scan=self.quick_scan_check.isChecked()
            )
            # Update UI from main thread
            QTimer.singleShot(0, self._scan_completed)

        thread = threading.Thread(target=run_scan, daemon=True)
        thread.start()

    def _update_scan_progress(self, scanned: int, total: int):
        """Update progress during scan"""
        QTimer.singleShot(0, lambda: self._set_progress(scanned, total))

    def _set_progress(self, scanned: int, total: int):
        """Set progress bar values (called from main thread)"""
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(scanned)
        self.status_label.setText(f"Scanned {scanned}/{total} hosts")

    def _scan_completed(self):
        """Handle scan completion"""
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        if not self._scan_result:
            self.status_label.setText("Scan failed")
            return

        result = self._scan_result
        self.status_label.setText(
            f"Scan complete: {result.plc_count} PLCs found, {result.issue_count} issues"
        )

        # Populate results table
        self.results_table.setRowCount(len(result.devices))
        for row, device in enumerate(result.devices):
            self.results_table.setItem(row, 0, QTableWidgetItem(device.ip_address))
            self.results_table.setItem(row, 1, QTableWidgetItem(device.hostname))
            self.results_table.setItem(row, 2, QTableWidgetItem(device.vendor))
            self.results_table.setItem(row, 3, QTableWidgetItem(device.model))
            ports = ", ".join(str(p.port) for p in device.open_ports)
            self.results_table.setItem(row, 4, QTableWidgetItem(ports))
            self.results_table.setItem(row, 5, QTableWidgetItem(str(len(device.security_issues))))

            # Color code based on issues
            if device.security_issues:
                max_risk = max(i.risk_level.value for i in device.security_issues)
                if max_risk == "critical":
                    color = QColor(255, 100, 100)
                elif max_risk == "high":
                    color = QColor(255, 180, 100)
                elif max_risk == "medium":
                    color = QColor(255, 255, 150)
                else:
                    color = QColor(200, 255, 200)

                for col in range(6):
                    item = self.results_table.item(row, col)
                    if item:
                        item.setBackground(color)

    def _stop_scan(self):
        """Stop ongoing scan"""
        self._scanner.cancel()
        self.status_label.setText("Scan cancelled")
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

    def _show_device_issues(self):
        """Show issues for selected device"""
        if not self._scan_result:
            return

        selected = self.results_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        if row < len(self._scan_result.devices):
            device = self._scan_result.devices[row]

            if device.security_issues:
                lines = [f"<h3>Security Issues for {device.ip_address}</h3>"]
                for issue in device.security_issues:
                    risk_color = {
                        "critical": "#ff0000",
                        "high": "#ff8800",
                        "medium": "#ffcc00",
                        "low": "#00aa00",
                        "info": "#0088ff"
                    }.get(issue.risk_level.value, "#888888")

                    lines.append(f"<p><b style='color:{risk_color}'>[{issue.risk_level.value.upper()}]</b> "
                               f"<b>{issue.title}</b><br/>"
                               f"{issue.description}<br/>"
                               f"<i>Recommendation: {issue.recommendation}</i></p>")

                self.issues_text.setHtml("".join(lines))
            else:
                self.issues_text.setHtml(f"<p>No security issues found for {device.ip_address}</p>")

    def _export_report(self):
        """Export scan report"""
        if not self._scan_result:
            QMessageBox.warning(self, "No Data", "Please run a scan first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Security Report",
            "plc_security_report.md",
            "Markdown (*.md);;All Files (*)"
        )

        if file_path:
            from plcforge.security.network_scanner import generate_security_report
            report = generate_security_report(self._scan_result)
            with open(file_path, 'w') as f:
                f.write(report)
            QMessageBox.information(self, "Export Complete", f"Report saved to:\n{file_path}")


def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("PLCForge")
    app.setOrganizationName("PLCForge")

    # Set application style
    app.setStyle("Fusion")

    # Initialize theme manager (dark mode by default)
    theme_manager = ThemeManager(app)
    theme_manager.set_theme(Theme.DARK)

    window = PLCForgeMainWindow()
    window.dark_mode_action.setChecked(True)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
