# https://code.activestate.com/recipes/578666-stopwatch-with-laps-in-tkinter/

import tkinter as tk
import time, os
import tracker as tr

class TrackerGui(tk.Frame):  
    """ Implements a stop watch frame widget. """                                                                
    def __init__(self, parent=None, **kw):        
        tk.Frame.__init__(self, parent, kw)
        self._start = 0.0        
        self._elapsedtime = 0.0
        self._running = 0
        self.timestr = tk.StringVar()
        #self.lapstr = tk.StringVar()
        self.e = 0
        self.m = 0
        self.makeWidgets()
        self.laps = []
        self.lapmod2 = 0
        self.today = time.strftime("%d %b %Y %H-%M-%S", time.localtime())
        
    def makeWidgets(self):                         
        """ Make the time label. """
        l1 = tk.Label(self, text='----File Name----')
        l1.pack(fill=tk.X, expand=tk.NO, pady=1, padx=2)

        self.e = tk.Entry(self)
        self.e.pack(pady=2, padx=2)
        
        l = tk.Label(self, textvariable=self.timestr)
        self._setTime(self._elapsedtime)
        l.pack(fill=tk.X, expand=tk.NO, pady=3, padx=2)

        l2 = tk.Label(self, text='----Laps----')
        l2.pack(fill=tk.X, expand=tk.NO, pady=4, padx=2)

        scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL)
        self.m = tk.Listbox(self,selectmode=tk.EXTENDED, height = 5,
                         yscrollcommand=scrollbar.set)
        self.m.pack(side=tk.LEFT, fill=tk.BOTH, expand=1, pady=5, padx=2)
        scrollbar.config(command=self.m.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
   
    def _update(self): 
        """ Update the label with elapsed time. """
        self._elapsedtime = time.time() - self._start
        self._setTime(self._elapsedtime)
        self._timer = self.after(50, self._update)
    
    def _setTime(self, elap):
        """ Set the time string to Minutes:Seconds:Hundreths """
        minutes = int(elap/60)
        seconds = int(elap - minutes*60.0)
        hseconds = int((elap - minutes*60.0 - seconds)*100)                
        self.timestr.set('%02d:%02d:%02d' % (minutes, seconds, hseconds))

    def _setLapTime(self, elap):
        """ Set the time string to Minutes:Seconds:Hundreths """
        minutes = int(elap/60)
        seconds = int(elap - minutes*60.0)
        hseconds = int((elap - minutes*60.0 - seconds)*100)            
        return '%02d:%02d:%02d' % (minutes, seconds, hseconds)
        
    def Start(self):                                                     
        """ Start the stopwatch, ignore if running. """
        if not self._running:            
            self._start = time.time() - self._elapsedtime
            self._update()
            self._running = 1        
    
    def Stop(self):                                    
        """ Stop the stopwatch, ignore if stopped. """
        if self._running:
            self.after_cancel(self._timer)            
            self._elapsedtime = time.time() - self._start    
            self._setTime(self._elapsedtime)
            self._running = 0
    
    def Reset(self):                                  
        """ Reset the stopwatch. """
        self._start = time.time()         
        self._elapsedtime = 0.0
        self.laps = []   
        self.lapmod2 = self._elapsedtime
        self._setTime(self._elapsedtime)


    def Lap(self):
        '''Makes a lap, only if started'''
        tempo = self._elapsedtime - self.lapmod2
        if self._running:
            self.laps.append(self._setLapTime(tempo))
            self.m.insert(tk.END, self.laps[-1])
            self.m.yview_moveto(1)
            self.lapmod2 = self._elapsedtime
       
    def GravaCSV(self):
        '''Pega nome do cronometro e cria arquivo para guardar as laps'''
        arquivo = str(self.e.get()) + ' - '
        with open(arquivo + self.today + '.txt', 'wb') as lapfile:
            for lap in self.laps:
                lapfile.write((bytes(str(lap) + '\n', 'utf-8')))
            
def main():
    print(os.getcwd())
    os.chdir("C:\\data\\engineering software\\utilities\\pomodoro")
    tt = tr.Tracker("log.txt") # This is the primary time tracker brain
    # plus the file it will log everything in
    tt.run()
    
    root = tk.Tk()
    root.wm_attributes("-topmost", 1)      #always on top - might do a button for it
    sw = TrackerGui(root)
    sw.pack(side=tk.TOP)

    tk.Button(root, text='Lap', command=sw.Lap).pack(side=tk.LEFT)
    tk.Button(root, text='Start', command=sw.Start).pack(side=tk.LEFT)
    tk.Button(root, text='Stop', command=sw.Stop).pack(side=tk.LEFT)
    tk.Button(root, text='Reset', command=sw.Reset).pack(side=tk.LEFT)
    tk.Button(root, text='Save', command=sw.GravaCSV).pack(side=tk.LEFT)
    # tk.Button(root, text='Quit', command=root.quit).pack(side=tk.LEFT)    
    
    root.mainloop()
    print("Finished.")
#    time.sleep(2)
    print(root)
    print("Actually finished.")

if __name__ == '__main__':
    main()