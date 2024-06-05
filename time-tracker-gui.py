

# Change log:
# 4/1/2022:
# Write active time and idle time to a permalog (timelogs.txt).
# Put old log files in "timelogs" folder.
# Idle time does not begin to accrue until 9:00.
# After the first 100 error messages, print no more than 1 per 1000 seconds.
# Active time cannot go negative due to being idle.
# At start of new day, record previous time as "Yesterday" instead of "None".
#
# Some other changes in May and June.
#
# 6/14/2022:
# Fixed bug that could cause elapsed time to be negative (b/c GetTickCount 
# can be negative).

# 7/21/2022: added mouse movement capability
# 9/14/2022: fixed bug related to accounting of idle time
# 9/15/2022: wiggle now shows minimized window, doesn't move cursor.
  # Added delay outside the try block in main loop, so it can't poll constantly
  # if there's an error accessing the log file.

# 3/22/2023: I tried to fix the issue of printing excessive error messages 
# when unable to access the image file or delete the tray icon.
# Also added a mechanism for turning off wiggle when not needed:
#  It will only wiggle if there's a file named wiggle.txt in the same folder.

# 1/19/2024: 
# Converted to a Qt program
# Added a checkbox for wiggle, and a display of the tail of the log file.
# To do:
# Add a quit program button, maybe
# Add pomodoros to the context menu?
# Make it read the log file on startup and pick up where it left off
# Graceful shutdown on computer reboot


import time
import datetime as dt
from datetime import datetime
from typing import Optional
import ctypes
from ctypes import wintypes, windll, create_unicode_buffer
import os
import sys
import shutil
import win32gui
import win32con
import win32api
import traceback
from PyQt5.QtWidgets import * #QApplication, QMainWindow, QSystemTrayIcon, QMenu, QAction, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QTimeEdit, QTextEdit, QLineEdit, QFileDialog
from PyQt5.QtGui import QIcon, QPixmap#, QPainter
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
import signal


class LastInputInfo(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('dwTime',wintypes.DWORD),
        ]


def winEnumHandler(windowx, ctx):
    if win32gui.GetWindowText(windowx).upper().endswith("GOOGLE CHROME"):
        #print(windowx, win32gui.GetWindowText(windowx))
        ctx.append(windowx)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, icon, parent):
        self.par = parent
        super(TrayIcon, self).__init__(icon, parent)
        self.setToolTip(f"Time Tracker")

        # Create the menu for the tray icon
        menu = QMenu(parent)

        # Add a 'Quit' action to the menu
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)

        # Set the context menu for the tray icon
        self.setContextMenu(menu)
    
    def set_icon(self, iconpath):
        self.setIcon(QIcon(iconpath))

    def quit(self):
        self.par.closeout()


class TrayApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowIcon(QIcon(os.path.join(os.getcwd(), "images", "clock.ico")))
        self.setWindowTitle("Time Tracker")
        self.resize(550, 350)


        self.timer = QTimer(self)
        self.timer.timeout.connect(self.run)
        self.timer.start(500)  # Call self.run() every 0.5 seconds

        self.wiggly = True

        pLastInputInfo = ctypes.POINTER(LastInputInfo)
        self.GetLastInputInfo = windll.user32.GetLastInputInfo
        self.GetLastInputInfo.restype = wintypes.BOOL
        self.GetLastInputInfo.argtypes = [pLastInputInfo]

        # Settings
        self.idle_timeout = 120*1000 # ms
        self.work_to_break_ratio = 2.5
        self.lunch_minutes = 45
        self.workday_start_hr = 7
        self.workday_start_min = 0
        self.workday_end_hr = 17
        self.workday_end_min = 30
        self.workdays = [0, 1, 2, 3, 4]

        self.windowdict = {}
        self.prevname = "None"
        self.liinfo = LastInputInfo()
        self.liinfo.cbSize = ctypes.sizeof(self.liinfo)
        self.idle_time = 0
        self.active_time = 0
        self.last_idle = time.time()
        self.last_active = time.time()
        self.last_change = time.time()
        self.prev_active_time = 0

        # keep track of number of error messages printed so we don't go too crazy.
        self.n_error_messages = 0
        self.max_error_messages = 100

        self.clockiconpath = os.path.join(os.getcwd(), "clock.ico")
        self.idleiconpath = os.path.join(os.getcwd(), "idle.ico")
        iconpath = self.clockiconpath
        #hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        # icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
        # hinst = win32api.GetModuleHandle(None)
        # hicon = win32gui.LoadImage(hinst, iconpath, win32con.IMAGE_ICON, 0, 0, icon_flags)
        # flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        self.hwnd = windll.user32.GetForegroundWindow()
        # nid = (self.hwnd, 0, flags, win32con.WM_USER+20, hicon, "Time Tracker")
        # #win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self.hwnd, 0))
        # try:
        #     win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        # except win32gui.error as e:
        #     self.n_error_messages += 1
        #     if self.n_error_messages < self.max_error_messages:
        #         print("Failed to make tray icon.", e)
        
        self.tray_icon = TrayIcon(QIcon(iconpath), self)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        self.tray_icon.activated.connect(self.tray_icon_clicked)
        self.tray_icon.show()
            
        # Set up to do continuous polling of what the active window is.
        self.filename = "time.log"
        self.permalog = "timelog.txt"

        self.last_change = os.path.getmtime(self.filename)
        
        self.init_ui()

        with open(self.filename, 'a') as logfile:
            logfile.write("Time tracker opened at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")
        
        self.i=0
        self.break_time = 0

        # Registering the signal handler
        signal.signal(signal.SIGTERM, self.graceful_shutdown)
        signal.signal(signal.SIGINT, self.graceful_shutdown)  # Handles Ctrl+C


        # Call self.run() every 0.5 s
        
            
    
    def init_ui(self):

        
        # Create the menu bar
        menubar = self.menuBar()

        # Create the file menu
        file_menu = menubar.addMenu('File')

        # Create the quit action
        quit_action = QAction('Quit', self)
        quit_action.setShortcut('Ctrl+Q')
        quit_action.triggered.connect(self.closeout)

        # Add the quit action to the file menu
        file_menu.addAction(quit_action)


        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()

        leftvlayout = QVBoxLayout()
        vlayout = QVBoxLayout()

        
        # Another display that shows the cumulative time spent in various windows
        # (windowdict)
        # Label for the windowdict display
        self.top_entries_label = QLabel("Cumulative time today:")
        vlayout.addWidget(self.top_entries_label)
        self.top_entries_display = QTextEdit()
        self.top_entries_display.setReadOnly(True)
        self.top_entries_display.setLineWrapMode(QTextEdit.NoWrap)
        vlayout.addWidget(self.top_entries_display)
        # Set a minimum height of 150
        self.top_entries_display.setMinimumHeight(150)
        # Minimum width of 300
        self.top_entries_display.setMinimumWidth(300)


        # Add labels for active time, idle time, and break time
        self.active_time_label = QLabel("Active time: 0")
        self.active_time_label.setFixedWidth(300)
        self.active_time_label.setFixedHeight(25)
        self.active_time_label.setAlignment(Qt.AlignLeft)
        self.active_time_label.setStyleSheet("font-size: 14pt;")  # Increase font size
        vlayout.addWidget(self.active_time_label)

        self.idle_time_label = QLabel("Idle time: 0")
        self.idle_time_label.setFixedWidth(300)
        self.idle_time_label.setFixedHeight(25)
        self.idle_time_label.setAlignment(Qt.AlignLeft)
        self.idle_time_label.setStyleSheet("font-size: 14pt;")  # Increase font size
        vlayout.addWidget(self.idle_time_label)

        self.break_time_label = QLabel("Break time earned: 0")
        self.break_time_label.setFixedWidth(300)
        self.break_time_label.setFixedHeight(25)
        self.break_time_label.setAlignment(Qt.AlignLeft)
        self.break_time_label.setStyleSheet("font-size: 14pt;")  # Increase font size
        vlayout.addWidget(self.break_time_label)

        # Add a checkbox for wiggle
        self.wiggle_checkbox = QCheckBox("Wiggle when idle during work hours to keep computer awake")
        self.wiggle_checkbox.setChecked(True)
        self.wiggle_checkbox.stateChanged.connect(self.wiggle_checkbox_changed)
        vlayout.addWidget(self.wiggle_checkbox)

        # Add controls for the user to specify the start and end time of the work day
        self.workday_start_label = QLabel("Workday starts at:")
        self.workday_start_label.setFixedWidth(150)
        self.workday_start_label.setFixedHeight(20)
        self.workday_start_label.setAlignment(Qt.AlignLeft)
        vlayout.addWidget(self.workday_start_label)


        self.workday_start_time = QTimeEdit()
        self.workday_start_time.setDisplayFormat("hh:mm")
        self.workday_start_time.setTime(QtCore.QTime(self.workday_start_hr, self.workday_start_min))
        self.workday_start_time.timeChanged.connect(self.work_time_changed)
        self.workday_start_time.setFixedWidth(50)
        vlayout.addWidget(self.workday_start_time)
        self.workday_end_label = QLabel("Workday ends at:")
        self.workday_end_label.setFixedWidth(150)
        self.workday_end_label.setFixedHeight(20)
        self.workday_end_label.setAlignment(Qt.AlignLeft)
        vlayout.addWidget(self.workday_end_label)
        self.workday_end_time = QTimeEdit()
        self.workday_end_time.setDisplayFormat("hh:mm")
        self.workday_end_time.setTime(QtCore.QTime(self.workday_end_hr, self.workday_end_min))
        self.workday_end_time.timeChanged.connect(self.work_time_changed)
        self.workday_end_time.setFixedWidth(50)
        vlayout.addWidget(self.workday_end_time)
        

        # Add checkboxes to specify which day of the week it should wiggle
        self.sunday_checkbox = QCheckBox("Sunday")
        self.monday_checkbox = QCheckBox("Monday")
        self.tuesday_checkbox = QCheckBox("Tuesday")
        self.wednesday_checkbox = QCheckBox("Wednesday")
        self.thursday_checkbox = QCheckBox("Thursday")
        self.friday_checkbox = QCheckBox("Friday")
        self.saturday_checkbox = QCheckBox("Saturday")

        self.monday_checkbox.setChecked(True)
        self.tuesday_checkbox.setChecked(True)
        self.wednesday_checkbox.setChecked(True)
        self.thursday_checkbox.setChecked(True)
        self.friday_checkbox.setChecked(True)

        for checkbox in [self.sunday_checkbox, self.monday_checkbox, self.tuesday_checkbox, self.wednesday_checkbox, self.thursday_checkbox, self.friday_checkbox, self.saturday_checkbox]:
            checkbox.stateChanged.connect(self.workday_checkbox_changed)
            vlayout.addWidget(checkbox)


        # Label for the log file display
        self.log_label = QLabel("Log file:")
        leftvlayout.addWidget(self.log_label)
        # Add a display that shows the tail of the log file
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QTextEdit.NoWrap)
        self.log_display.setMinimumWidth(300)
        #self.log_display.setFixedWidth(400)
        #self.log_display.setFixedHeight(200)
        leftvlayout.addWidget(self.log_display)


        layout.addLayout(leftvlayout)
        layout.addLayout(vlayout)
        # show the layout
        central_widget.setLayout(layout)
    
    def wiggle_checkbox_changed(self, state):
        if state == QtCore.Qt.Checked:
            self.wiggly = True
            for checkbox in [self.sunday_checkbox, self.monday_checkbox, self.tuesday_checkbox, self.wednesday_checkbox, self.thursday_checkbox, self.friday_checkbox, self.saturday_checkbox]:
                checkbox.setEnabled(True)
        else:
            self.wiggly = False
            # Disable the day of the week checkboxes if wiggly is false
            for checkbox in [self.sunday_checkbox, self.monday_checkbox, self.tuesday_checkbox, self.wednesday_checkbox, self.thursday_checkbox, self.friday_checkbox, self.saturday_checkbox]:
                checkbox.setEnabled(False)
    
    def workday_checkbox_changed(self, state):
        # Set workdays based on the checkboxes
        self.workdays = []
        for i, checkbox in enumerate([self.monday_checkbox, self.tuesday_checkbox, self.wednesday_checkbox, self.thursday_checkbox, self.friday_checkbox, self.saturday_checkbox, self.sunday_checkbox]):
            if checkbox.isChecked():
                self.workdays.append(i)

    def work_time_changed(self):
        self.workday_start_hr = self.workday_start_time.time().hour()
        self.workday_start_min = self.workday_start_time.time().minute()
        self.workday_end_hr = self.workday_end_time.time().hour()
        self.workday_end_min = self.workday_end_time.time().minute()

    def getForegroundWindowTitle(self) -> Optional[str]:
        hwindow = windll.user32.GetForegroundWindow()
        length = windll.user32.GetWindowTextLengthW(hwindow)
        buf = create_unicode_buffer(length + 1)
        windll.user32.GetWindowTextW(hwindow, buf, length + 1)
        if buf.value:
            return buf.value
        else:
            return None

    
    def wiggle(self):
    
        # Check what window is in focus
        fgwindow = windll.user32.GetForegroundWindow()
        # Find a Microsoft Teams window
        teamswindows = []
        win32gui.EnumWindows(winEnumHandler, teamswindows) 
        if len(teamswindows) == 0:
            print("No teams window found.")
           
            return
        # Show it and switch to it
        win32gui.ShowWindow(teamswindows[0], win32con.SW_SHOWNORMAL)
        windll.user32.SetForegroundWindow(teamswindows[0])
        print("Teams window to foreground")
        time.sleep(0.1)
        
        # Check if it's the same one that was already in focus
        # If so, find something else to switch to ("Program Manager" window)
        defaultwindows = []
        if teamswindows[0] == fgwindow:
            def winEnumHandlerDefault(windowx, ctx):
                if win32gui.GetWindowText(windowx).startswith("Program Manager"):
                    ctx.append(windowx)
            win32gui.EnumWindows(winEnumHandlerDefault, defaultwindows)
            if len(defaultwindows) > 0:
                fgwindow = defaultwindows[0]
        # Switch away from Teams window
        text = win32gui.GetWindowText(fgwindow)
        windll.user32.SetForegroundWindow(fgwindow)
        print(text, "window to foreground")

    def wait_until_active(self, tol=1):
        self.liinfo = LastInputInfo()
        self.liinfo.cbSize = ctypes.sizeof(self.liinfo)
        lasttime = None
        delay = 100
        maxdelay = int(tol*1000)
        t_idle = time.time()
        awakefor = 1000*60*90 # stay awake 90 minutes after last active
        while True:
            self.GetLastInputInfo(ctypes.byref(self.liinfo))
            if lasttime is None: 
                lasttime = self.liinfo.dwTime
                print("Last moved by user at", lasttime)
            #print("Last moved at", self.liinfo.dwTime)
            if lasttime != self.liinfo.dwTime:
                break
            stayawake = False
            d = datetime.now()
            if d.weekday() in self.workdays:
                if d.hour >= self.workday_start_hr and d.hour < self.workday_end_hr:
                    if time.time() - t_idle < awakefor:
                        stayawake = True
                        #print("Stayawake true")
            if self.wiggly and stayawake:
                self.wiggle()
                self.GetLastInputInfo(ctypes.byref(self.liinfo))
                lasttime = self.liinfo.dwTime
                #print("Wiggled at", time.time())
            delay = min(2*delay, maxdelay)
            windll.kernel32.Sleep(delay)
            #print("Sleeping")


    def tray_icon_clicked(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # Typically a left-click
            if self.isHidden():
                self.show()
                self.activateWindow()
                self.raise_()
            else:
                self.hide()
        elif reason == QSystemTrayIcon.Context:  # Right-click, show context menu
            # The context menu should be shown automatically by the QSystemTrayIcon
            pass


    def update_icon(self, hwnd, activetime, idle=False, breaktime=0):
        # Update the icon to show the current active time
        if idle:
            self.tray_icon.set_icon(self.idleiconpath)
        else:
            self.tray_icon.set_icon(self.clockiconpath)
        iconstring = "Time Tracker: " + str(activetime) + " hrs active"
        iconstring += ". " + str(round(breaktime/60,1)) + " minutes of breaks earned."
        self.tray_icon.setToolTip(iconstring)
        return hwnd


    def run(self):
        # Update the log display.
        try:
            log_file_changed = False
            # check if the log file has changed
            if os.path.exists(self.filename):
                if os.path.getmtime(self.filename) > self.last_change:
                    log_file_changed = True
                    self.last_change = os.path.getmtime(self.filename)

            if log_file_changed:
                with open(self.filename, 'r') as logfile:
                    # I want the last 20 lines
                    lines = logfile.readlines()
                    tail = "".join(lines[-20:])
                self.log_display.setText(tail)
        except Exception as e:
            print("Error accessing log file.", e)
            time.sleep(0.5)
            return
        
        # Update the windowdict display
        sortedwindows = sorted(self.windowdict.items(), key=lambda x:x[1], reverse=True)
        top_entries = ""
        for k in sortedwindows:
            top_entries += str(round(k[1])) + " s\t" + k[0].encode("ascii", "ignore").decode() + "\n"
        self.top_entries_display.setText(top_entries)
        
        # Update the labels
        self.active_time_label.setText("Active time: " + str(round(self.active_time/3600,2)) + " hrs")
        self.idle_time_label.setText("Idle time: " + str(round(self.idle_time/3600,2)) + " hrs")
        self.break_time_label.setText("Break time earned: " + str(round(self.break_time/60,1)) + " mins")

        # Update active time, idle time, break time, etc, and write to the log.
        try:
            self.i += 1
            if self.i % 1000 == 0 and self.n_error_messages > 0:
                self.n_error_messages -= 1

            # Check if focus window has changed, if so record the time spent on the last one
            try:
                winname = self.getForegroundWindowTitle()
            except Exception as e:
                winname = "Unreadable window name"
                print(e)
            try:
                if winname is None:
                    winname = "None"
                if winname != self.prevname:
                    if not (self.prevname in self.windowdict.keys()):
                        self.windowdict[self.prevname] = time.time() - self.last_change
                    else:
                        self.windowdict[self.prevname] += time.time() - self.last_change
                    self.last_change = time.time()
            except Exception as e:
                print(e)
                with open(self.filename, 'a') as logfile:
                    self.n_error_messages += 1
                    if self.n_error_messages < self.max_error_messages:
                        logfile.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " \t" + "Error 1 in: " + winname + "\n")
            try:
                if winname != self.prevname:
                    with open(self.filename, 'a') as logfile:
                        try:
                            logfile.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " \t" + winname.encode("ascii", "ignore").decode() + "\n")
                        except: 
                            self.n_error_messages += 1
                            if self.n_error_messages < self.max_error_messages:
                                logfile.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " \t" + "Error 2 in window name:" + repr(winname) + "\n")
                    self.prevname = winname
            except Exception as e:
                print(e)
                with open(self.filename, 'a') as logfile:
                    self.n_error_messages += 1
                    if self.n_error_messages < self.max_error_messages:
                        logfile.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " \t" + "Error 3 in: " + winname + "\n")
            
            # For the case where the computer was put to sleep by the user (not idle):
            # Check if it's a new day (with cutoff at 4am) and make a new file if so.
            date_last_active = (datetime.fromtimestamp(self.last_active) - dt.timedelta(hours=4)).date()
            date_now = (datetime.now() - dt.timedelta(hours=4)).date()
            if date_now != date_last_active and time.time() - self.last_active > 10.0:
                with open(self.filename, 'a') as logfile:
                    sortedwindows = sorted(self.windowdict.items(), key=lambda x:x[1], reverse=True)
                    for k in sortedwindows:
                        logfile.write("\t" + str(round(k[1])) + "\t" + k[0].encode("ascii", "ignore").decode() + "\n")
                    logfile.write("\nSwitching to new log file (end of day). ")
                    logfile.write("Active time: " + str(round(self.active_time)) + "(" + \
                            str(round(self.active_time/3600,2)) + ")\t Idle time: " + str(round(self.idle_time)) + "\t Break time earned: " + str(round(self.break_time/60,1)) + " minutes." + "\n")
                oldfilename = "time" + str(date_last_active.month) + "-" + str(date_last_active.day) + "-" + str(date_last_active.year) + ".log"
                shutil.move(os.path.join(os.getcwd(), self.filename), os.path.join(os.getcwd(), "timelogs", oldfilename))

                # Subtract a day from today
                yesterday = datetime.now() - dt.timedelta(days=1)
                with open(self.permalog, 'a') as logfile:
                    logfile.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\nData for " + yesterday.strftime("%Y-%m-%d") + " \t" + "Active time: " + \
                            str(round(self.active_time/3600,2)) + "\t Idle time: " + str(round(self.idle_time/3600,2)) + " \t Break time earned: " + str(round(self.break_time/60,1)) + " minutes." + "\n")
                self.windowdict = {}
                self.prevname = "Yesterday"
                self.active_time = 0
                self.windowdict["idletime"] = 0
                self.idle_time = 0
                last_idle = time.time()
                self.last_active = time.time()
            
            # Update total active time
            since_last_active = time.time() - self.last_active
            self.active_time += since_last_active
            self.last_active = time.time()
            round_active_time = round(self.active_time/3600.,2)
            self.break_time = self.active_time / self.work_to_break_ratio - self.idle_time
            if datetime.now().hour >= 13 and self.idle_time > self.lunch_minutes*60:
                self.break_time += self.lunch_minutes*60
            if round_active_time != self.prev_active_time:
                self.hwnd = self.update_icon(self.hwnd, round_active_time, breaktime=self.break_time)
                self.prev_active_time = round_active_time

            
            
            # Check if idle
            self.GetLastInputInfo(ctypes.byref(self.liinfo))
            g = windll.kernel32.GetTickCount()
            while g < 0: g += 2**32
            elapsed = g - self.liinfo.dwTime
            #print(GetTickCount(), self.liinfo.dwTime, elapsed)
            if elapsed >= self.idle_timeout or since_last_active > self.idle_timeout/1000:
                # Became idle, now record what happened and wait for something to move.
                #active_time -= idle_timeout/1000 #+= time.time() - last_active - idle_timeout/1000
                self.active_time -= self.idle_timeout/1000 + since_last_active
                self.active_time = max(self.active_time, 0)
                self.idle_time += self.idle_timeout/1000 + since_last_active
                
                # Fix idle time if it's including time before start of workday.
                now = datetime.now()
                seconds_since_workday_start = (now - now.replace(hour=self.workday_start_hr, minute=self.workday_start_min, second=0, microsecond=0)).total_seconds()
                self.idle_time = min(self.idle_time, max(0, seconds_since_workday_start))
                
                last_idle = self.last_active #time.time() - idle_timeout/1000
                with open(self.filename, 'a') as logfile:
                    logfile.write((datetime.now() - dt.timedelta(seconds=self.idle_timeout/1000)).strftime("%Y-%m-%d %H:%M:%S") + " \tBecame idle. Active " + \
                                str(round(self.active_time)) + " (" + str(round(self.active_time/3600, 2)) + ") " + "\t Idle: " + str(round(self.idle_time)) +"\n")
                    #print("active ", time.time() - last_idle - idle_timeout/1000, time.time(), last_idle)

                if not (self.prevname in self.windowdict.keys()):
                    self.windowdict[self.prevname] = time.time() - self.last_change
                else:
                    self.windowdict[self.prevname] += time.time() - self.last_change
                self.last_change = time.time() - self.idle_timeout/1000
                # For debugging:
                with open(self.filename, 'a') as logfile: 
                    logfile.write("last_change is " + str(self.last_change) + "\n")
                oldprevname = self.prevname
                self.prevname = "idletime"
                self.hwnd = self.update_icon(self.hwnd, round_active_time, True)
                
                self.wait_until_active()
                
                # If the user does something within 10 seconds of the icon showing that they're idle,
                # then cancel the idle period (assume they were just looking at the screen).
                with open(self.filename, 'a') as logfile: 
                    logfile.write("time.time() is " + str(time.time()) + "\n")
                if time.time() - self.last_change < self.idle_timeout/1000 + 10:
                    with open(self.filename, 'a') as logfile:
                        logfile.write("Idle period cancelled.\n")
                        logfile.write("time.time() is " + str(time.time()) + "\n")
                    self.idle_time -= self.idle_timeout/1000
                    self.active_time += self.idle_timeout/1000
                    self.prevname = oldprevname
                
                round_active_time = round(self.active_time/3600.,2)
                self.break_time = self.active_time / self.work_to_break_ratio - self.idle_time
                self.hwnd = self.update_icon(self.hwnd, round_active_time, breaktime=self.break_time) # not necessary maybe, b/c active time changes when it becomes idle.
                
                # Check if it's a new day (with cutoff at 4am) and make a new file if so.
                date_last_active = (datetime.fromtimestamp(self.last_active) - dt.timedelta(hours=4)).date()
                date_now = (datetime.now() - dt.timedelta(hours=4)).date()
                # rename existing log file with the date of the last time user was active.
                if date_now != date_last_active:
                    with open(self.filename, 'a') as logfile:
                        sortedwindows = sorted(self.windowdict.items(), key=lambda x:x[1], reverse=True)
                        for k in sortedwindows:
                            logfile.write("\t" + str(round(k[1])) + "\t" + k[0].encode("ascii", "ignore").decode() + "\n")
                        logfile.write("\nSwitching to new log file (end of day). ")
                        logfile.write("Active time: " + str(round(self.active_time)) + "(" + \
                                str(round(self.active_time/3600,2)) + ")\t Idle time: " + str(round(self.idle_time)) + "\n")
                    oldfilename = "time" + str(date_last_active.month) + "-" + str(date_last_active.day) + "-" + str(date_last_active.year) + ".log"
                    shutil.move(os.path.join(os.getcwd(), self.filename), os.path.join(os.getcwd(), "timelogs", oldfilename))
                    with open(self.permalog, 'a') as logfile:
                        logfile.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " \t" + "Active time: " + \
                                str(round(self.active_time/3600,2)) + "\t Idle time: " + str(round(self.idle_time/3600,2)) + " \t Break time earned: " + str(round(self.break_time/60,1)) + " minutes." + "\n")
                    self.windowdict = {}
                    self.prevname = "Yesterday"
                    self.windowdict["idletime"] = 0 # reset idle time total
                    self.active_time = 0
                    self.idle_time = 0
                    last_idle = time.time()
                
                with open(self.filename, 'a') as logfile:
                    logfile.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " \tBecame active. Active " + \
                                str(round(self.active_time)) + " (" + str(round(self.active_time/3600, 2)) + ") " + "\t Idle: " )
                now = datetime.now()
                seconds_since_workday_end = (now - now.replace(hour=self.workday_end_hr, minute=self.workday_end_min, second=0, microsecond=0)).total_seconds()
                if seconds_since_workday_end < 0:
                    self.idle_time += time.time() - last_idle
                else:
                    new_idle_time = time.time() - last_idle
                    if new_idle_time > seconds_since_workday_end:
                        self.idle_time += new_idle_time - seconds_since_workday_end
                
                with open(self.filename, 'a') as logfile:
                    logfile.write(str(round(self.idle_time)) +"\n")
                
                self.last_active = time.time()
                self.liinfo = LastInputInfo()
                self.liinfo.cbSize = ctypes.sizeof(self.liinfo)
                
                now = datetime.now()
                seconds_since_workday_start = (now - now.replace(hour=self.workday_start_hr, minute=self.workday_start_min, second=0, microsecond=0)).total_seconds()
                self.idle_time = max(0, min(self.idle_time, seconds_since_workday_start))
            
            # stop or write out current stats if directed by user creation of a file
            if os.path.exists(os.path.join(os.getcwd(), "stop.txt")):
                self.closeout()
            if os.path.exists(os.path.join(os.getcwd(), "show.txt")):
                self.show_log_file()
                
        # Write any errors to the log file
        except Exception as e:
            trace = ''.join(traceback.format_exc())
            errorline = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " \tError: " + repr(e) + "\n" + trace + "\n"
            with open(self.filename, 'r') as logfile:
                for line in logfile:
                    pass
                last_line = line
            if last_line != errorline:
                try:
                    with open(self.filename, 'a') as logfile:
                        self.n_error_messages += 1
                        if self.n_error_messages < self.max_error_messages:
                            logfile.write(errorline)
                except Exception as e:
                    print("Error that couldn't be logged.", e)

    def show_log_file(self):
        self.active_time += time.time() - self.last_active
        with open(self.filename, 'a') as logfile:
            # Write stats
            logfile.write("\t\t\tLast became active: " + str(time.time() - self.last_active) + " seconds ago.\n")
            
            sortedwindows = sorted(self.windowdict.items(), key=lambda x:x[1], reverse=True)
            for k in sortedwindows:
                logfile.write("\t" + str(round(k[1])) + "\t" + k[0].encode("ascii", "ignore").decode() + "\n")
            logfile.write("Active time: " + str(round(self.active_time)) + "(" + \
                    str(round(self.active_time/3600,2)) + ")\t Idle time: " + str(round(self.idle_time)) + "\t Break time earned: " + str(round(self.break_time/60,1)) + " minutes." + "\n")
        self.last_active = time.time()
        if os.path.exists(os.path.join(os.getcwd(), "show.txt")):
            os.remove(os.path.join(os.getcwd(), "show.txt"))

    def graceful_shutdown(self, signum, frame):
        # Perform your cleanup operations here
        self.closeout()

    def closeout(self):

        # Separate this final portion into two functions, 
        # one that just writes the current data to the logfile and another that handles the stuff for closing the program.

        # Wrap up and write results before closing.
        with open(self.filename, 'a') as logfile:
            # Write stats
            self.active_time += time.time() - self.last_active
            logfile.write("\nWindows:\n")
            sortedwindows = sorted(self.windowdict.items(), key=lambda x:x[1], reverse=True)
            for k in sortedwindows:
                logfile.write("\t" + str(round(k[1])) + "\t" + k[0].encode("ascii", "ignore").decode() + "\n")
            logfile.write("Active time: " + str(round(self.active_time)) + "(" + \
                        str(round(self.active_time/3600,2)) + ")\t Idle time: " + str(round(self.idle_time)) + "\t Break time earned: " + str(round(self.break_time/60,1)) + " minutes.")
            logfile.write("\nTime tracker closed at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n\n\n")
            with open(self.permalog, 'a') as logfile:
                logfile.write("Closed at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " \t" + "Active time: " + \
                        str(round(self.active_time/3600,2)) + "\t Idle time: " + str(round(self.idle_time/3600,2)) + " \t Break time earned: " + str(round(self.break_time/60,1)) + " minutes." + "\n")
            if os.path.exists(os.path.join(os.getcwd(), "stop.txt")):
                os.remove(os.path.join(os.getcwd(), "stop.txt"))
        
        # Get rid of tray icon
        self.tray_icon.hide()

        
        QApplication.quit()

        # quit program
        exit()



if __name__ == "__main__":
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    tray_app = TrayApp()
    tray_app.show()
    tray_app.run()
    app.exec_()
