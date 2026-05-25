from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_voice_bridge.ui.settings import ShortcutEditorState, normalize_key_name


def test_normalize_key_name_maps_modifiers_and_special_keys():
    assert normalize_key_name("Control_L") == "CTRL"
    assert normalize_key_name("Shift_R") == "SHIFT"
    assert normalize_key_name("space") == "SPACE"
    assert normalize_key_name("a") == "A"


def test_shortcut_editor_state_records_sorted_accelerator():
    state = ShortcutEditorState()

    state.begin_capture().update_pressed(["space", "Control_L", "Shift_L"]).finish_capture()

    assert state.accelerator == "ctrl+shift+space"
    assert [pill.key for pill in state.pills] == ["CTRL", "SHIFT", "SPACE"]
    assert state.caption == "Shortcut saved"
    assert all(pill.pressed is False for pill in state.pills)


def test_shortcut_editor_detects_conflict_and_can_clear():
    state = ShortcutEditorState()

    state.begin_capture().update_pressed(["Alt_L", "F4"]).finish_capture(conflict_with="Windows close window")

    assert state.conflict == "Windows close window"
    assert state.caption == "Windows close window"

    state.clear()

    assert state.accelerator == ""
    assert state.listening is False
    assert state.pills == []
    assert state.caption == "Click to record shortcut"


def test_shortcut_editor_can_load_existing_accelerator():
    state = ShortcutEditorState()

    state.load_accelerator("ctrl+shift+space")

    assert state.accelerator == "ctrl+shift+space"
    assert [pill.key for pill in state.pills] == ["CTRL", "SHIFT", "SPACE"]
    assert state.caption == "CTRL + SHIFT + SPACE"
