"""
Dwarf - Copyright (C) 2019 Giovanni Rocca (iGio90)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>
"""
import threading

import frida

from lib import utils
from lib.adb import Adb
from lib.core import Dwarf
from ui.menu_bar import MenuBar

from PyQt5.QtWidgets import *

from ui.ui_session import SessionUi
from ui.ui_welcome import WelcomeUi


class AppWindow(QMainWindow):
    def __init__(self, dwarf_args, flags=None, *args, **kwargs):
        super().__init__(flags, *args, **kwargs)

        self.app = App(self)
        self.adb = Adb()

        self.dwarf = Dwarf(self)

        self.update_title()

        self.setCentralWidget(self.app)
        self.app.setup_ui()

        self.menu = MenuBar(self)
        if dwarf_args.package is not None:
            # we skip welcome ui here
            if not self.get_adb().available():
                # additional check if we have a local server to starts with
                if frida.get_local_device() is None:
                    utils.show_message_box('adb/device/emu not found or not rooted! see details or output',
                                           self.app.get_adb().get_states_string())
                    return

            if dwarf_args.spawn is not None:
                err = self.dwarf.spawn(dwarf_args.package, dwarf_args.script)
            else:
                err = self.dwarf.attach(dwarf_args.package, dwarf_args.script, print_debug_error=False)
                if err > 0:
                    if err == 1:
                        # no device? kidding?
                        pass
                    elif err == 2:
                        # no proc to attach - fallback to spawn
                        err = self.dwarf.spawn(dwarf_args.package, dwarf_args.script)

    def get_adb(self):
        return self.adb

    def get_app_instance(self):
        return self.app

    def on_context_info(self):
        self.get_menu().on_context_info()

    def get_dwarf(self):
        return self.dwarf

    def get_menu(self):
        return self.menu

    def on_script_destroyed(self):
        self.menu.on_script_destroyed()
        self.app.on_script_destroyed()

    def on_script_loaded(self):
        self.menu.on_script_loaded()
        self.app.on_script_loaded()

    def update_title(self, title_str="Dwarf"):
        self.setWindowTitle(title_str)


class App(QWidget):
    def __init__(self, app_window, flags=None, *args, **kwargs):
        super().__init__(flags, *args, **kwargs)

        self.app_window = app_window

        self.box = QVBoxLayout()
        self.box.setContentsMargins(0, 0, 0, 0)

        self.welcome_ui = None
        self.session_ui = None

    def setup_ui(self):
        self.session_ui = SessionUi(self)
        self.welcome_ui = WelcomeUi(self)

        self.session_ui.hide()

        self.box.addWidget(self.welcome_ui)
        self.box.addWidget(self.session_ui)

        self.setLayout(self.box)

    def restart(self):
        self.dwarf_api('restart')
        self.resume()

    def resume(self, tid=0):
        if tid == 0:
            self.get_contexts_lists_panel().setRowCount(0)
            self.get_context_panel().setRowCount(0)
            self.get_backtrace_panel().setRowCount(0)
            self.get_memory_panel().clear_panel()
            self.get_dwarf().contexts.clear()
            if self.get_java_explorer_panel() is not None:
                self.get_java_explorer_panel().clear_panel()

        self.dwarf_api('release', tid)

    def on_tid_resumed(self, tid):
        if self.get_dwarf().context_tid == tid:
            self.get_context_panel().setRowCount(0)
            self.get_backtrace_panel().setRowCount(0)
            self.get_memory_panel().clear_panel()
            if self.get_java_explorer_panel() is not None:
                self.get_java_explorer_panel().clear_panel()

        self.get_contexts_lists_panel().resume_tid(tid)

    def clear(self):
        self.modules_panel.setRowCount(0)
        self.ranges_panel.setRowCount(0)
        self.session_ui.console_panel().clear()

    def set_modules(self, modules):
        self.session_ui.modules_panel.set_modules(modules)

    def set_ranges(self, ranges):
        self.session_ui.ranges_panel.set_ranges(ranges)

    def _apply_context(self, context):
        if 'modules' in context:
            self.set_modules(context['modules'])
        if 'ranges' in context:
            self.set_ranges(context['ranges'])
        if 'context' in context:
            is_java = context['is_java']
            if is_java:
                self.get_context_panel().set_context(context['ptr'], 1, context['context'])
                self.get_java_explorer_panel().set_handle_arg(-1)
            else:
                self.get_context_panel().set_context(context['ptr'], 0, context['context'])

    def apply_context(self, context):
        threading.Thread(target=self._apply_context, args=(context,)).start()

    def dwarf_api(self, api, args=None, tid=0):
        return self.get_dwarf().dwarf_api(api, args=args, tid=tid)

    def get_adb(self):
        return self.app_window.get_adb()

    def get_asm_panel(self):
        return self.session_ui.asm_panel

    def get_backtrace_panel(self):
        return self.session_ui.backtrace_panel

    def get_context_panel(self):
        return self.session_ui.context_panel

    def get_contexts_lists_panel(self):
        return self.session_ui.contexts_list_panel

    def get_data_panel(self):
        return self.session_ui.data_panel

    def get_dwarf(self):
        return self.app_window.get_dwarf()

    def get_emulator_panel(self):
        return self.session_ui.emulator_panel

    def get_ftrace_panel(self):
        return self.session_ui.ftrace_panel

    def get_hooks_panel(self):
        return self.session_ui.hooks_panel

    def get_java_classes_panel(self):
        return self.session_ui.java_class_panel

    def get_java_explorer_panel(self):
        return self.session_ui.java_explorer_panel

    def get_java_trace_panel(self):
        return self.session_ui.java_trace_panel

    def get_console_panel(self):
        return self.session_ui.console_panel

    def get_memory_panel(self):
        return self.session_ui.memory_panel

    def get_modules_panel(self):
        return self.session_ui.modules_panel

    def get_pointer_size(self):
        return self.pointer_size

    def get_ranges_panel(self):
        return self.session_ui.ranges_panel

    def get_session_ui(self):
        return self.session_ui

    def get_trace_panel(self):
        return self.session_ui.trace_panel

    def get_watchers_panel(self):
        return self.session_ui.watchers_panel

    def on_script_destroyed(self):
        self.session_ui.hide()
        self.session_ui.on_script_destroyed()

        self.welcome_ui.show()
        self.welcome_ui.update_device_ui()

    def on_script_loaded(self):
        self.session_ui.on_script_loaded()

        self.welcome_ui.hide()
        self.session_ui.show()

        # trigger this to clear lists
        self.welcome_ui.on_devices_updated()
