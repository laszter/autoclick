import sys
import os
import threading
import time
import pandas as pd

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QMenu
)
from pynput import keyboard, mouse
from pynput.mouse import Button, Controller

try:
    from ctypes import windll  # Only exists on Windows.
    myappid = 'laszter.autoclick.click.1'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

mouse_listener = None
mouse_listening = False
mouse_clicks = []
mouse_playing = False
mouse_playing_loop = False
mouse_click_delay = 1000

class mouseEvent:
    def __init__(self, event, position, time):
        self.event = event
        self.position = position
        self.time = time

def mouse_click_thread():
    global mouse_clicks
    global mouse_playing

    mouse_controller = Controller()
    mouse_playing = True
    while mouse_playing:
        for click in mouse_clicks:
            mouse_move_animation(mouse_controller.position, click.position, click.time / 1000)
            if not mouse_playing:
                break
            print('Click : {0}'.format(click.position))
            mouse_controller.position = click.position
            mouse_controller.press(Button.left)
            mouse_controller.release(Button.left)
        if not mouse_playing_loop and mouse_playing:
            print('Stopped playing mouse clicks')
            window.change_text_play('Press F2 to start playing')
            mouse_playing = False
            break

def mouse_move_animation(startPos, endPos, duration):
    global mouse_playing

    mouse_controller = Controller()
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time < duration:
        if not mouse_playing:
            break
        elapsed_time = time.time() - start_time
        if elapsed_time > duration:
            break
        progress = elapsed_time / duration
        x = startPos[0] + (endPos[0] - startPos[0]) * progress
        y = startPos[1] + (endPos[1] - startPos[1]) * progress
        mouse_controller.position = (x, y)
        time.sleep(0.001)

def update_table():
    global mouse_clicks
    global window

    data_table = []
    for click in mouse_clicks:
        data_table.append([click.event, click.position, click.time])

    window.update_table_data(data_table)

def on_click(x, y, button, pressed):
    global mouse_clicks
    global mouse_click_delay

    if pressed:
        print('{0} at {1} {2}'.format('Pressed' if pressed else 'Released', button, (x, y)))
        
        mouse_clicks.append(mouseEvent(button, (x,y), mouse_click_delay))
        update_table()

def on_press(key):
    global mouse_listener
    global mouse_listening
    global mouse_clicks
    global mouse_playing
    
    if key == keyboard.Key.f1 and mouse_listening == False:
        mouse_listening = True
        print('Collecting mouse clicks')
        mouse_listener = mouse.Listener(on_click=on_click)
        mouse_listener.start()
        window.change_text_record('Press F1 to stop recording')
        return True

    if key == keyboard.Key.f1 and mouse_listening == True:
        mouse_listener.stop()
        mouse_listening = False
        print('Stopped collecting mouse clicks')
        window.change_text_record('Press F1 to start recording')
        return True
        
    if key == keyboard.Key.f2:
        if mouse_listening == True:
            mouse_listener.stop()
            mouse_listening = False
            print('Stopped collecting mouse clicks')
            window.change_text_record('Press F1 to start recording')

        if len(mouse_clicks) > 0:
            if mouse_playing:
                mouse_playing = False
                print('Stopped playing mouse clicks')
                window.change_text_play('Press F2 to start playing')
                return True
            
            print('Playing mouse clicks')
            click_thread = threading.Thread(target=mouse_click_thread)
            click_thread.start()
            window.change_text_play('Press F2 to stop playing')
        else:
            print('No clicks collected')

        return True
        
    if key == keyboard.Key.esc:
        mouse_playing = False
        # Stop listener
        return False

class TableModel(QtCore.QAbstractTableModel):
    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            
            return str(value)

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        return self._data.shape[1]
    
    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])

            if orientation == Qt.Orientation.Vertical:
                return str(self._data.index[section])
            
    def rightClickMenu(self, position):
        menu = QMenu()
        edit = menu.addAction("Edit")
        delete = menu.addAction("Delete")
        action = menu.exec_(self.viewport().mapToGlobal(position))
        if action == edit:
            print('Edit')
        elif action == delete:
            print('Delete')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Auto Click")
        self.setFixedSize(600, 400)

        page_layout = QVBoxLayout()
        list_layout = QHBoxLayout()

        self.table = QtWidgets.QTableView()
        self.table.verticalHeader().hide()

        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)

        self.update_table_data([])
        list_layout.addWidget(self.table)

        menu_layout = QVBoxLayout()
        menu_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        menu_layout.addWidget(QLabel('Delay (ms)'))
        self.inputTimer = QLineEdit()
        self.inputTimer.setText('1000')
        self.inputTimer.setValidator(QtGui.QIntValidator())
        self.inputTimer.textChanged.connect(self.click_delay_update)
        menu_layout.addWidget(self.inputTimer)

        menu_layout.addWidget(QLabel('Loop'))
        self.inputLoop = QtWidgets.QCheckBox()
        self.inputLoop.stateChanged.connect(self.click_loop_update)
        menu_layout.addWidget(self.inputLoop)

        self.clearButton = QPushButton('Clear')
        self.clearButton.clicked.connect(self.clear_table)
        menu_layout.addWidget(self.clearButton)

        self.recordLabel = QLabel('Press F1 to start recording')
        menu_layout.addWidget(self.recordLabel)

        self.playLabel = QLabel('Press F2 to start playing')
        menu_layout.addWidget(self.playLabel)

        list_layout.addLayout(menu_layout)

        page_layout.addLayout(list_layout)

        widget = QWidget()
        widget.setLayout(page_layout)
        self.setCentralWidget(widget)

        listener = keyboard.Listener(on_press=on_press)
        listener.start()

        self.show()

    def update_table_data(self, data):
        self.model = TableModel(pd.DataFrame(data, columns = ['Event', 'Position', 'Time']))
        self.table.setModel(self.model)

    def click_delay_update(self, text):
        global mouse_click_delay
        mouse_click_delay = int(text)

    def click_loop_update(self):
        global mouse_playing_loop
        mouse_playing_loop = self.inputLoop.isChecked()

    def clear_table(self):
        global mouse_clicks
        mouse_clicks = []
        self.update_table_data([])

    def change_text_record(self, text):
        self.recordLabel.setText(text)

    def change_text_play(self, text):
        self.playLabel.setText(text)

basedir = os.path.dirname(__file__)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join(basedir, "icon.ico")))

    window = MainWindow()
    app.exec()
