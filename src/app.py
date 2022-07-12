import pathlib
from numpy import append
import ui
import data
import player
import stream
import argparse
import asyncio
import time
import sys
import input
import threading
import traceback
from rich import print
import rich.live
import rich.panel
import rich.text
import rich.markup
import rich.console

class app:
    """
    App
    ===
    provides UI application.
    """
    def __init__(self,console:rich.console.Console=rich.console.Console(),*,browser_dir:pathlib.Path=pathlib.Path.home(),ui_mode:bool=True):
        """
        __init__
        ========
        
        ### Arguments:
        - console : set console for output.
        - browser : set home directory for browser.
        - ui : the flag for using ui.
        """
        self.stream=None
        self.stop=False
        self.queue_clear_chk=False
        self.api_actions=[]
        self.stopchk=False
        self.repeat=0 #0 -> no repeat 1 -> repeat queue 2 -> repeat a song
        self.queue=data.queue()
        self.is_ui_enable=ui_mode
        self.ui=ui.ui()
        self.ui.browser.set_location(browser_dir)
        self.keyrepeat=10
        self.player=None
        self.playing:asyncio.Task=None
        self.eventloop=asyncio.get_event_loop()
        self.informationText:str=""
        self.selecting_mode=False
        self.console=console
    def open(self,volume):
        self.stream:stream.stream=stream.stream(volume)
    def play(self,file,ext):
        self.player=player.advanced_player()
        self.player.load(file,ext)
        self.playing=self.eventloop.run_until_complete(self.stream.play(self.player))
    def ui_update(self):
        if self.player == None or self.stream.info==None:
            info={}
        else:info=self.stream.info
        info["volume"]=self.stream.volume if self.stream is not None else 100
        info["pause"]=self.stream.pause
        info["mute"]=self.stream.mute
        info["repeat"]=self.repeat
        info["selection_mode"]=self.selecting_mode
        self.ui.update(info,self.queue,rich.panel.Panel(rich.text.Text.from_markup("[red]Do you really want to delete item(s)?\n[green3](C to delete selected/focused item(s).)\n(Enter or Shift+C to clear queue)")) if self.queue_clear_chk else None,"Exit player? [y/n]" if self.stopchk else self.informationText)
    @property
    def volume(self):return self.stream.volume if self.stream is not None else 100
    @volume.setter
    def volume(self,val):
        if val<0:val=0
        if val>150:val=150
        if self.stream is not None:self.stream.volume=val
    @property
    def timeline(self):return 0 if self.stream is None else self.stream.timeline
    @timeline.setter
    def timeline(self,time):
        if time < 0:time=0
        if self.stream is None:return
        self.stream.timeline=time
    def queue_mainloop(self):
        try:
            while True:
                last_playing=self.queue.playing
                time.sleep(0.1)
                if self.stop:break
                if self.queue.playing is None:
                    if len(self.queue)==0:
                        self.queue.playing=None
                        continue
                    if (self.queue.playing is None):
                        if self.stream.pause:self.queue.playing=0
                        continue
                if last_playing!=self.queue.playing:
                    time.sleep(1)
                    continue

                self.api_action("play",self.queue.playing)

                self.play(*self.queue.queue[self.queue.playing].path)
                if not self.stream.getback:
                    if self.repeat in (0,1):
                        if self.queue.playing >= len(self.queue)-1:
                            if self.repeat==0:
                                self.queue.playing=None
                                self.stream.pause=True
                            else:
                                self.queue.playing=0
                        else:self.queue.playing+=1
                    if len(self.queue)==0:
                        self.stream.pause=True
        except KeyboardInterrupt:pass
        except Exception as e:
            print(e)
            traceback.print_tb(sys.exc_info()[2])
    def ui_mainloop(self):
        listener = input.input(self.on_press).start()
        try:
            with rich.live.Live(self.ui.prepare(),refresh_per_second=15):
                while True:
                    self.ui_update()
                    if self.stop:break
                    time.sleep(0.05)
        except KeyboardInterrupt:pass
        listener.stop=True
        print(rich.panel.Panel("[green3]Are there no prompt? Press any key to show.\n[purple]And let's visit [link=https://beatbox4108.tk]me[/link].",title="PlayQuick INFORMATION"))
    def mainloop(self):
        self.eventloop.run_in_executor(None,self.queue_mainloop)
        if self.is_ui_enable:self.ui_mainloop()
        else: self.api()
    def on_press(self,key):
        if self.keyrepeat>0:self.keyrepeat-=1
        if key==b"q":self.stopchk=not self.stopchk
        if key==b"K":self.volume-=10
        elif key in ("f2",b"k"):self.volume-=1
        if key==b"I":self.volume+=10
        elif key in ("f3",b"i"):self.volume+=1

        if key in ("f5",b" "):
            if self.stream is not None:self.stream.pause=not self.stream.pause     
        if key=="f1":
            if self.stream is not None:self.stream.mute=not self.stream.mute     

        if key=="LEFT":
            if self.stream is not None:self.timeline-=int(5000/(1 if self.player is None else self.player.CHUNK))
        if key=="RIGHT":
            if self.stream is not None:self.timeline+=int(5000/(1 if self.player is None else self.player.CHUNK))
        
        if key==b"s":
            self.selecting_mode=not self.selecting_mode

        if key in ("UP",b"u",b"U"):
            if self.ui.tab==0:
                self.ui.browser.index-=1
                self.ui.browser.update()
            elif self.ui.tab==1:
                self.ui.q_builder.update(self.queue)
                self.ui.q_builder.index-=1
                
                if not self.selecting_mode:
                    self.ui.q_builder.selection_index=self.ui.q_builder.index
                    self.ui.q_builder.cancel_selecting()
        if key in ("DOWN",b"j",b"J"):
            if self.ui.tab==0:
                self.ui.browser.index+=1
                self.ui.browser.update()
            elif self.ui.tab==1:
                self.ui.q_builder.update(self.queue)
                self.ui.q_builder.index+=1
                if not self.selecting_mode:
                    self.ui.q_builder.selection_index=self.ui.q_builder.index
                    self.ui.q_builder.cancel_selecting()

        if key == b"\r":
            self.ui.browser.open()
            self.ui.browser.update()
        
        if key in (b"1",b"2",b"3") and self.ui.browser._openchk:
            if self.ui.browser._focus is None:pass
            elif key==b"1":
                self.queue.append(data.song(self.ui.browser._focus))
            elif key==b"2":
                self.queue.insert(0,data.song(self.ui.browser._focus))
                self.queue.playing=0
                self.stream.getback=True
            elif key==b"3":
                self.queue.clear()
                self.queue.append(data.song(self.ui.browser._focus))
                self.queue.playing=0
                self.stream.getback=True
            self.ui.browser._openchk=False
            self.stream.pause=False
        elif key==b"1":self.ui.tab=0
        elif key==b"2":self.ui.tab=1
        elif key==b"3":self.ui.tab=2
        if key in ("f7",b"r"):
            self.repeat+=1
            if self.repeat==3:self.repeat=0
        if True:#self.keyrepeat<=0:
            if key=="f4":
                self.queue.playing-=1
                self.stream.getback=True
                self.keyrepeat=5
            elif key=="f6":
                self.queue.playing+=1
                self.stream.getback=True
                self.keyrepeat=5
        if key==b"p":
            if self.ui.tab==1:
                self.ui.property_tab.set_property(data.propertydata().read_from_song(self.ui.q_builder.queue.queue[self.ui.q_builder.index]))
            if self.ui.tab==0:
                self.ui.property_tab.set_property(data.propertydata().read_from_file(self.ui.browser._listdir_raw[self.ui.browser.index]))
            self.ui.tab=2

        if key == "backspace":
            self.queue_clear_chk=True
        if self.queue_clear_chk:
            if key in (b"\r",b"C"):
                self.queue.clear()
                self.queue.playing=None
                self.stream.getback=True
                self.queue_clear_chk=False
            elif key==b"c":
                self.queue.remove_items(self.ui.q_builder._selection)
                self.queue_clear_chk=False
                self.ui.q_builder.update(self.queue)
            elif key in (b"C","backspace"):pass
            else:self.queue_clear_chk=False


        if self.stopchk:
            if key == b"y":
                self.stop=True
                if self.playing != None:self.playing.cancel()
            elif key == b"n":self.stopchk=False

    def api(self,stdin=sys.stdin,stdout=sys.stdout):
        while True:
            if self.stop:break
            while True:
                data=stdin.readline()
                if data=="":break
                data=data.split(" ")
                if data[0]=="get":
                    if len(data) < 2:break
                    if data[1]=="queue":
                        if len(data) < 3:
                            self.api_action("result",*(i.replace(" ","\\ ") for i in self.queue.queue))
                        if data[2]=="playing":
                            self.api_action("result",self.queue.playing)
                        if data[2]=="song":
                            if len(data) < 4:break
                            if data[3]=="info":
                                if len(data) < 5:self.api_action("result"," ".join(str(i) for i in (self.queue.queue[self.queue.playing]).path))
                                try:
                                    song=self.queue.queue[int(data[4])]
                                    if len(data) < 6:self.api_action("result"," ".join(str(i) for i in song.path))
                                    if data[5]=="title":
                                        self.api_action("result",song.title)
                                    if data[5]=="album":
                                        self.api_action("result",song.album)
                                    if data[5]=="artist":
                                        self.api_action("result",song.artist)
                                    if data[5]=="path":
                                        self.api_action("result"," ".join(str(i) for i in song.path))
                                except:break
                if data[0]=="exit":self.stop=True


                    
            while len(self.api_actions)!=0:
                task=self.api_actions.pop(0)
                if task[0]=="play":stdout.write(f"play {task[1][0]}")
                elif task[0]=="result":stdout.write(" ".join(task))
                stdout.flush()
            time.sleep(0.1)
    
    def api_action(self,action,*args,**kwargs):
        if not self.is_ui_enable:self.api_actions.append(action,args,kwargs)

if __name__=="__main__":
    a=app()
    a.open()
    loop=asyncio.get_event_loop()
    try:
        a.mainloop()
    except KeyboardInterrupt:pass
    except Exception as e:
        rich.console.Console().print_exception()
    sys.exit()
        
