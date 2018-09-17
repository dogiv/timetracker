

import os
import sys
from infi.systray import SysTrayIcon
import time
from PIL import Image, ImageFont, ImageDraw
import ctypes
from datetime import datetime
import subprocess
import random
#import workflowy

class Timer:
    def __init__(self, filename):
        self.not_quit = True
        self.standby = True
        self.pause = False
        self.pause_time = -1
        self.end_hour = 0
        self.end_minute = 0
        self.end_second = 0
        self.message = u"Take a break!"
        self.get_input = True # whether to ask for input when the timer ends
        self.filename = filename
        self.break_time = 5
        self.long_break_time = 10
        self.work_time = 25
        self.long_work_time = 45
        self.mins_remaining = -1
        self.wait_time = -1
        self.points = 0
        self.points_used_now = 0 # points used so far during the current break
        self.work_multiplier = 0.6 # points earned per minute of 100% productive work
        self.last_wait_time = -1
        self.work = False
        self.rest = False
        self.prev_work = False
        self.prev_rest = False
        self.last_checked_log = 0
        with open(self.filename,'a') as logfile:
            logfile.write("Timer opened at "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")
        self.check_log()
    def check_log(self, systray=None):
        if time.time() - self.last_checked_log > 2: # min 2 seconds between file reads
            #print("checking log")
            with open(self.filename,'r') as logfile:
                logs = logfile.readlines()
            pointer = len(logs) - 1
            while not logs[pointer].startswith("Total points:"): # find the last line in the log file that lists the point total
                pointer = pointer - 1
                if pointer < 0:
                    with open(self.filename,'a') as logfile:
                        logfile.write("Total points: " + str(round(self.points,1)) + "\n")
                    break
            if pointer >= 0: # add up points earned and spent since the last total
                self.points = float(logs[pointer].split()[2])
                points_since = 0
                while pointer < len(logs):
                    #print("Pointer is " + str(pointer))
                    if logs[pointer].startswith("Points earned:"):
                        points_since += float(logs[pointer].split()[2])
                        #print("Found points earned.\n")
                    if logs[pointer].startswith("Points used:"):
                        points_since -= float(logs[pointer].split()[2])
                        #print("Found points used.")
                        #print(logs[pointer])
                        #print(logs[pointer].split()[2])
                        #print(float(logs[pointer].split()[2]))
                        #print(points_since)
                    pointer += 1
                self.points += points_since
                #print(points_since)
                #print(self.points)
                if not points_since == 0: # only write the total if it has changed
                    #print("writing")
                    with open(self.filename,'a') as logfile:
                        logfile.write("Total points: " + str(round(self.points,1)) + "\n")
            self.last_checked_log = time.time()
    def on_quit_callback(self,systray):
        self.cancel(systray)
        time.sleep(0.3)
        self.not_quit = False
        self.standby = False
        with open(self.filename,'a') as logfile:
            logfile.write("Timer shut down at "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")
    def start_break(self,systray):
        print("Break!")
        self.rest = True
        self.work = False
        self.get_input = False
        with open(self.filename,'a') as logfile:
            logfile.write(str(self.break_time)+" minute break started at "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")
        self.start_pomodoro(systray, wait=self.break_time, message=u"Break done!", get_input=False)
    def long_break(self,systray):
        print("Long break!")
        self.rest = True
        self.work = False
        self.get_input = False
        with open(self.filename,'a') as logfile:
            logfile.write(str(self.long_break_time)+" minute break started at "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")
        self.start_pomodoro(systray, wait=self.long_break_time, message=u"Long break finished!", get_input=False)
    def long_pomodoro(self,systray):
        print("Deep work pomodoro!")
        self.rest = False
        self.work = True
        self.get_input = True
        with open(self.filename,'a') as logfile:
            logfile.write(str(self.long_work_time)+" minute pomodoro started at "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")
        self.start_pomodoro(systray, wait=self.long_work_time, message=u"Take a long break! Rate productivity from 1-10: ", get_input=True)
    def start_pomodoro(self,systray, wait=-1, message=u"Time to take a break! Rate productivity from 1-10: ", get_input=True):
        if wait < 0:
            wait = self.work_time
            self.rest = False
            self.work = True
            self.get_input = True
            print("Pomodoro!")
            with open(self.filename,'a') as logfile:
                logfile.write(str(self.work_time)+" minute pomodoro started at "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")
        #self.mins_remaining = wait
        self.wait_time = wait
        self.points_used_now = 0
        self.message = message
        self.get_input = get_input
        # Get time when program is started
        dt = list(time.localtime())
        wait # minutes
        self.last_wait_time = wait
        self.end_hour = dt[3]
        self.end_minute = dt[4] + wait
        self.end_second = dt[5]
        if self.end_minute > 59:
            self.end_minute = self.end_minute - 60
            self.end_hour += 1
        if self.end_minute < 10:
            end_minute_str = "0" + str(self.end_minute)
        else:
            end_minute_str = str(self.end_minute)
        print("Ending at " + str(self.end_hour) + ":" + end_minute_str)
        self.end_time = time.time() + wait*60
        self.standby = False
        self.pause = False
    def cancel(self,systray):
        self.standby = True
        if self.work:
            with open(self.filename,'a') as logfile:
                logfile.write("Canceled at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")
            subprocess.Popen(['python.exe', 'input.py', str(self.get_input), "Canceled! " + self.message, str(self.wait_time - (self.end_time - time.time())/60),str(self.work_multiplier)])
        elif self.rest:
            with open(self.filename,'a') as logfile:
                logfile.write("Canceled at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")
                logfile.write("Points used: " + str(self.wait_time - (self.end_time - time.time())/60) + "\n")
        self.work = False
        self.rest = False
        print("Canceled!")
    def togglepause(self,systray):
        self.pause = not self.pause # toggle
        self.pause_time = self.end_time - time.time()
        if self.pause:
            print("Paused! " + str(round(self.pause_time/60,1)) + " minutes left.")
            self.prev_work = self.work
            self.prev_rest = self.rest
            self.work = False
            self.rest = False
        else:
            dt = list(time.localtime())
            self.pause_time = self.end_time - time.time()
            self.end_hour = dt[3]
            #print(self.end_hour)
            #print(self.pause_time)
            self.end_minute = dt[4] + self.pause_time / 60
            #print(self.end_minute)
            self.end_second = dt[5]
            if self.end_minute > 59:
                self.end_minute = self.end_minute - 60
                self.end_hour += 1
            if self.end_minute < 10:
                end_minute_str = "0" + str(self.end_minute)
            else:
                end_minute_str = str(self.end_minute)
            self.work = self.prev_work
            self.rest = self.prev_rest
            print("Continuing. Ending at " + str(self.end_hour) + ":" + end_minute_str)
   
if __name__ == '__main__':
    

    print(os.getcwd())
    os.chdir("C:\\data\\engineering software\\utilities\\pomodoro")
    timer1 = Timer("log.txt")
    timer1.not_quit = True
    timer1.standby = True
    timer1.check_log()
    top_message = str(timer1.points) + " points"
    menu_opts = (("Start break", None, timer1.start_break),("Long break", None, timer1.long_break),("Start Pomodoro", None, timer1.start_pomodoro,),("Long Pomodoro", None, timer1.long_pomodoro,),("Cancel", None, timer1.cancel,),("Pause/Unpause", None, timer1.togglepause,))

    systray = SysTrayIcon("clock.ico", str(timer1.points) + " points", menu_opts, on_quit=timer1.on_quit_callback, default_menu_index=2)
    systray.start()
    secs_rem = -1
    counter = 0
    t_since = 80
    
##    # Every day at 8:50, 9-16:20 and 12:55 check Workflowy for reminders with today's date
##    workflowy_hour = [8, 9, 10, 11, 12, 12, 13, 14, 15, 16, 17]
##    workflowy_minute = [50, 20, 20, 20, 20, 55, 20, 20, 20, 20, 20]
##    workflowy_checked = False
##    new_reminders = workflowy.WorkflowyScheduler.get_reminders()
##    reminders = new_reminders
##    # write reminders to log file
##    with open(timer1.filename,'a') as logfile:
##        logfile.write("Reminders for " + "@%s" % time.strftime("%a%d%b%Y  %H:%M:%S") + ":\n")
##        for line in reminders.split("\n"):
##            logfile.write(line + " not_notified")
    
    
    while(timer1.not_quit):
        
##        # check if there are reminders to show
##        dt = list(time.localtime())
##        hour = dt[3]
##        minute = dt[4]
##        if hour in workflowy_hour and minute == workflowy_minute[workflowy_hour.index(hour)] and workflowy_checked == False:
##            # check workflowy
##            new_reminders = workflowy.WorkflowyScheduler.get_reminders()
##            reminders += new_reminders
##            workflowy_checked = True
##        if hour in workflowy_hour and minute - 1 == workflowy_minute[workflowy_hour.index(hour)]: # set the flag back 1 minute later
##            workflowy_checked = False
        
        
        # run the timer
        if timer1.standby:
            time.sleep(0.05)
            if counter == 40:
                counter = 0
                timer1.check_log()
                systray.update(hover_text=str(timer1.points) + " points")
            counter += 1
        else:
            icon_image = None
            if timer1.work:
                icon_image = Image.new('RGB', (16,16), (0,0,0)) #black
            if timer1.rest:
                icon_image = Image.new('RGB', (16,16), (0,80,40)) #green background for rest
            draw = ImageDraw.Draw(icon_image)
            font = ImageFont.truetype("./arial.ttf", 14)
            timer1.mins_remaining = round((timer1.end_time - time.time())/60)
            draw.text((0, 0),str(timer1.mins_remaining),(255,255,255),font=font)
            icon_image.save("current.ico", sizes=[(16,16)])
            systray.update(icon="current.ico")
            systray.update(hover_text="Timer in progress! " + str(timer1.points) + " points")
            #print("updated")
            secs_rem = 0
            while(not timer1.standby):
                dt = list(time.localtime())
                if timer1.pause == True:
                    timer1.end_time = time.time() + timer1.pause_time
                #hour = dt[3]
                #minute = dt[4]
                #if hour == timer1.end_hour and minute == timer1.end_minute:
                if timer1.end_time - time.time() < 0.01:
                    print("Done!")
                    #message_im = Image.new('RGB', (256, 256))
                    #draw = ImageDraw.Draw(message_im)
                    #font = ImageFont.truetype("./arial.ttf", 20)
                    #draw.text((0, 0),timer1.message,(255,255,255),font=font)
                    #message_im.show()
                    #os.startfile("Break.jpg")
                    #ctypes.windll.user32.MessageBoxW(None, timer1.message, u"Timer Done\n", 0)
                    timer1.standby = True
                    #os.startfile("input.py")
                    if timer1.work:
                        multiplier = timer1.work_multiplier # points are earned at a rate of 0.6 per productive minute worked
                    if timer1.rest:
                        multiplier = 1.0 # points are used at a rate of 1.0 per minute of rest
                    # Pop up a cmd window to show that the timer is done, and maybe ask for a productivity rating.
                    subprocess.Popen(['python.exe', 'input.py', str(timer1.get_input), timer1.message, str(timer1.wait_time),str(multiplier)])
                    timer1.work = False
                    timer1.rest = False
                    
                time.sleep(0.2)
                t_since += 0.2
                if t_since > 100 and timer1.work:
                    if random.randrange(int(30*60/0.2)) == 1: # Every 30 minutes on average
                        message_im = Image.new('RGB', (256, 256))
                        draw = ImageDraw.Draw(message_im)
                        font = ImageFont.truetype("./arial.ttf", 20)
                        draw.text((0, 0),"Check-in!",(255,255,255),font=font)
                        #message_im.show()
                        t_since = 0
                new_mins_rem = int(round((timer1.end_time - time.time())/60))

                #if new_mins_rem < 0:
                #    new_mins_rem += 60
                if new_mins_rem != timer1.mins_remaining and new_mins_rem > 0:
                    if timer1.rest:
                        timer1.points_used_now = timer1.wait_time - new_mins_rem
                        systray.update(hover_text=str(timer1.points - timer1.points_used_now) + " points")
                    timer1.mins_remaining = new_mins_rem
                    if timer1.work:
                        icon_image = Image.new('RGB', (16,16), (0,0,0)) #black
                    if timer1.rest:
                        icon_image = Image.new('RGB', (16,16), (0,80,40)) #green background for rest
                    draw = ImageDraw.Draw(icon_image)
                    font = ImageFont.truetype("./arial.ttf", 14)
                    if timer1.mins_remaining > 4:
                        textcolor = (255,255,255)
                    else:
                        textcolor = (255,100,0)
                    icon_text = str(timer1.mins_remaining)
                    draw.text((0, 0),icon_text,textcolor,font=font)
                    icon_image.save("current.ico", sizes=[(16,16)])
                    systray.update(icon="current.ico")
                    print("Changed remaining time.")
                    time.sleep(0.1)
                if timer1.end_time - time.time() <= 60:
                    #sec = dt[5]
                    new_secs_rem = int(round(timer1.end_time - time.time()))
                    if new_secs_rem != secs_rem:
                        icon_text = str(secs_rem)
                        if timer1.work:
                            icon_image = Image.new('RGB', (16,16), (0,0,0)) #black
                        if timer1.rest:
                            icon_image = Image.new('RGB', (16,16), (0,80,40)) #green background for rest
                        draw = ImageDraw.Draw(icon_image)
                        textcolor = (255,100,0)
                        draw.text((0, 0),icon_text,textcolor,font=font)
                        icon_image.save("current.ico", sizes=[(16,16)])
                        systray.update(icon="current.ico")
                        secs_rem = new_secs_rem
            systray.update("clock.ico")
            #systray.shutdown()
            timer1.standby = True
            t_since = 80
            with open(timer1.filename,'a') as logfile:
                logfile.write("Timer went off at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"\n")
        
    #time.sleep(0.01)
    print("quit")
    systray.shutdown()
    quit()


# To do 8/4/2017:
# Tally total effective minutes worked in a day.
# Have pop-ups during pomodoros (every 5-10 minutes? but random) that ask if I was thinking about work. If so, I get a piece of gum.
# Maybe add a "take away a point" menu item that I can use to get a piece of gum?
