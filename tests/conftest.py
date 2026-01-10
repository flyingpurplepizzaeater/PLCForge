"""Pytest configuration and fixtures for PLCForge tests."""

import pytest
from pathlib import Path


@pytest.fixture
def temp_project_file(tmp_path):
    """Create a temporary TIA Portal project file."""
    import zipfile

    project_xml = """<?xml version="1.0" encoding="utf-8"?>
<Document>
  <Engineering version="V17">
    <Project Name="TestProject">
      <Device Name="PLC_1">
        <DeviceItem Name="CPU 1516-3 PN/DP">
        </DeviceItem>
      </Device>
    </Project>
  </Engineering>
</Document>"""

    project_path = tmp_path / "test_project.ap17"

    with zipfile.ZipFile(project_path, 'w') as zf:
        zf.writestr("project.xml", project_xml)

    return project_path
