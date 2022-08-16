import asyncio
import collections
import os
import pathlib
import shutil
import string
import sys
import time
import typing
from importlib.resources import path

import rich
import rich.layout
import rich.style
import rich.table
import rich.text
from rich import print
from rich.columns import Columns
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table

from . import data,localization as i18n


class fs_browser:
    def __init__(self,i18n:i18n.Locarization=i18n.Locarization.read()) -> None:
        self.browser=Layout()
        self.i18n=i18n
        self._=i18n.get
        self._location:pathlib.Path=pathlib.Path.home()
        self._location_is_root:bool=False
        self._listdir:list=[]
        self._listdir_raw:list=[pathlib.Path("..")]
        self._index=0
        self.make_location_list()
        self._openchk=False
        self._focus=None
    def get(self):
        return self.browser
    def make_location_list(self):
        if self._location_is_root and os.name=="nt":
            self._listdir_raw=[pathlib.Path('%s:' % d) for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
        else:self._listdir_raw=[pathlib.Path(".."),*(self._location.glob("*"))]
        
        self._listdir=[" ".join((("[green3]" if self.__class__.is_codec_avaliable(f.suffix.lstrip(".")) else "")+("d" if f.is_dir() else "f" if f.is_file() else "l" if f.is_symlink() else "s" if f.is_char_device() or f.is_block_device() else"?"),str(f) if f.name=="" else f.name)) for f in self._listdir_raw]
    def scrolled(self,index):
        if self._openchk:return Panel(rich.text.Text.from_markup(self._("ui.browser.check_open.message")),title=rich.text.Text.from_markup(self._("ui.browser.check_open.title")))
        d=self._listdir[:]
        table=Table.grid(expand=True)
        if (len(d) > index):d[index]="[reverse]"+d[index]
        for i,s in enumerate(d):
            if self.index-5 > i:continue
            table.add_row(s)
        
        
        return table
    def update(self):
        if not self._openchk:self._focus=None
        self.column=self.scrolled(self._index)
        self.browser.split_column(
            Layout(rich.text.Text.from_markup(self._("ui.browser.header").format(self._location.resolve())),size=2),
            self.column
        )
        return self
    @property
    def index(self):return self._index
    @index.setter
    def index(self,n):self._index=(0 if n<0 else len(self._listdir)-1 if n>=len(self._listdir)-1 else n)
    def open(self):
        if self._openchk:
            self._openchk=False
            return
        if self._listdir_raw[self._index].is_file():
            self._openchk=True
            self._focus=self._listdir_raw[self._index]
        elif self._listdir_raw[self._index].is_symlink() or self._listdir_raw[self._index].is_dir():
            if len(self._location.parents)==0 and self._listdir_raw[self._index].name==".." and os.name=="nt":
                self._location_is_root=True
            elif self._location_is_root:
                self._location=pathlib.Path(self._listdir_raw[self._index])/"/"
                self._location_is_root=False
            else:
                self._location=(self._location/self._listdir_raw[self._index]).resolve()
            self.make_location_list()
            self._index=0
    @staticmethod
    def avaiable_codecs():
        return data.avaliable_codecs
    @classmethod
    def is_codec_avaliable(cls,codec):
        return codec in cls.avaiable_codecs()

    def set_location(self,loc):
        self._location=pathlib.Path(loc)
        self.make_location_list()


class queue_builder:
    def __init__(self,i18n:i18n.Locarization=i18n.Locarization.read()) -> None:
        self._table=Table()
        self.i18n=i18n
        self._=i18n.get
        self._focus_index=0
        self._selection_index=0
        self._selection=data.selection()
        self.queue:data.queue=data.queue()
        self.eventloop=asyncio.get_event_loop()
    def get(self):return self._table
    def update(self,queue:data.queue):
        self.queue.load(self.eventloop)
        self._table=Table(expand=True,show_header=True,show_lines=False)
        self.queue=queue
        self.make_selection()
        self.index=self.index
        for c in [
                self._("ui.queue.row.playing"),
                self._("ui.queue.row.tracknum"),
                self._("ui.queue.row.title"),
                self._("ui.queue.row.artist"),
                self._("ui.queue.row.album"),
                self._("ui.queue.row.filetype"),
                self._("ui.queue.row.path")
            ]:
            self._table.add_column(c)
        for i,s in enumerate(queue.queue):
            if self._focus_index-5 > i:continue
            self._table.add_row(*(">" if i==queue.playing else " ")+str(i),s.title,s.artist,s.album,s._path.suffix,str(s._path),style=rich.style.Style(color=("green3" if self._selection.is_in(i) else "purple" if self.queue.playing==i else None)))
        return self
    @property
    def index(self):return self._focus_index
    @index.setter
    def index(self,val):
        self._focus_index,val=(0 if val<0 else len(self.queue)-1 if val>len(self.queue)-1 else val),self._focus_index
    @property
    def selection_index(self):return self._selection_index
    @index.setter
    def selection_index(self,val):
        self._selection_index=0 if val<0 else len(self.queue)-1 if val>len(self.queue)-1 else val
        self.make_selection()
    def cancel_selecting(self):
        self._selection_index=self._focus_index
    def make_selection(self):
        self._selection=data.selection(self._selection_index,self._focus_index)
    

class property_tab:
    def __init__(self,i18n:i18n.Locarization=i18n.Locarization.read()) -> None:
        self.data:typing.Union[data.propertydata,None]=None
        self.i18n=i18n
        self._=i18n.get
    def set_property(self,propertydata:data.propertydata):
        self.data=propertydata
    def get(self):return Panel(self._("ui.property.none")) if self.data is None else self.data.table



class tabs_manager:
    def __init__(self,tabs) -> None:
        self._tabs=tabs
        self._index=0
    def swicher(self,index):self._index=index
    def get(self,noneval=None):
        try: return self._tabs[self._index]
        except IndexError:return noneval


class ui:
    class nonepacker:
        def __init__(self,o):self.o=o
        def get(self):return o
    def __init__(self,i18n:i18n.Locarization=i18n.Locarization.read()) -> None:
        self.data_default={"time":0,"time_length":1,"title":"-","album":"UNKNOWN","artist":"UNKNOWN","volume":100,"pause":False,"mute":False}
        self._tab=0
        self.i18n=i18n
        self._=i18n.get
        self._message=""
        self.layout=Layout()
        self.player=Layout(size=7)
        self.browser=fs_browser(i18n=i18n)
        self.q_builder=queue_builder(i18n=i18n)
        self.property_tab=property_tab(i18n=i18n)
        self.tabmgr=tabs_manager([self.browser,self.q_builder,self.property_tab])
    @staticmethod
    def tabs(tabs,selected)->Panel:
        return rich.text.Text.from_markup("[underline]|[/]".join([(f"[green]{t}[/]" if selected==i else f"[underline]{t}[/]") for i,t in enumerate(tabs)]))
    def titles(self,data):
        return rich.text.Text.from_markup(\
            self._("ui.player.title").format(data["title"])+" "+\
            self._("ui.player.artist").format(data["artist"])+" "+\
            self._("ui.player.album").format(data["album"])+" "\
            )
    def time_and_volume(self,data):
        table=Table.grid(expand=True)
        table.add_column()
        table.add_row(
            rich.text.Text("{}/{} ".format(
                time.strftime("%H:%M:%S",time.gmtime(0 if data["time"]is None else data["time"])),
                time.strftime("%H:%M:%S",time.gmtime(0 if data["time_length"]is None else data["time_length"]))
            )),
            rich.text.Text.from_markup(
                self._("ui.player.volume").format(
                    v=str(data['volume']).rjust(3),
                    m=(self._("ui.player.volume.muted") if data['mute'] else self._("ui.player.volume.unmuted")),
                    i=self.volume_indicator(data['volume'])
                )
                ,justify="right"
            )
        )
        return table
    def is_terminal_is_enough(self,ts:typing.Union[tuple,os.terminal_size])->bool:
        if ts[0]<48:return False
        if ts[1]<24:return False
        return True
    def update(self,info,queue,custom_panel=None,message=" "):
        self._message=message
        self.browser.update()
        self.q_builder.update(queue)
        self.layout.split_column(
            Layout(rich.text.Text.from_markup(self._("ui.selectionmode")+(self._("ui.selectionmode.on") if info.get("selection_mode") else self._("ui.selectionmode.off"))),size=1),
            Layout((self.tabs([self._("ui.tab.filesystem"),self._("ui.tab.queue"),self._("ui.tab.property")],self._tab)),size=1),
            (self.tabmgr.get(noneval=[self.__class__.nonepacker(Panel(self._("ui.tab.error")))]).get()) if custom_panel is None else custom_panel,
            self.player
        )
        
        data=collections.ChainMap(info,self.data_default)
        size=shutil.get_terminal_size()
        hsize=6
        wsize=size[0]-5

        self.player.split_column(
            rich.text.Text(self._("ui.player.header").format(data["title"]),justify="center"),
            Layout(self.titles(data),height=2),
            self.time_and_volume(data),
            self.get_timeline(data,wsize),
            rich.text.Text(f"|◀◀ (F4) ◀◀ (←) {'▶' if data['pause'] else '▮▮'} (F5) ▶▶ (→) ▶▶| (F6)",justify="center"),
            rich.text.Text.from_markup(self._("ui.player.repeat").format(({0:self._('ui.player.repeat.no'),1:self._('ui.player.repeat.queue'),2:self._('ui.player.repeat.song')})[data['repeat']]),justify="center"),
            rich.text.Text(" " if self._message=="" else self._message)
        )
    def prepare(self):
        if not self.is_terminal_is_enough(shutil.get_terminal_size()):return Panel(rich.text.Text(f"Sorry, but your terminal is too small for me...\nYou need a terminal bigger than 48x24 (You're now {tuple(shutil.get_terminal_size())})\nTo get a prompt, please press esc. Next, press any key.",justify="center"),title="PlayQuick WARNING")

        return self.layout#text.replace("\n ","\n")
    
    def get_timeline(self,data,size):
        time_percent=(0 if data["time"]==None else data["time"])/(1 if data["time_length"]== None else data["time_length"])*100
        return rich.text.Text("",justify="center").append("━"*int(time_percent/100*size-1),"blue").append("･","yellow bold").append("━"*(size-1-int(time_percent/100*size-1)),"")
    def volume_indicator(self,vol):
        vol=int(vol/10)
        return "\033[34m" + ("-"*(vol-1)) + "\033[33m･" + "\033[0m" + ("-"*(15-vol))[:14]
    
    @property
    def tab(self):
        return self._tab
    @tab.setter
    def tab(self,value):
        self._tab=value
        self.tabmgr.swicher(value)
        


if __name__=="__main__":
    u=ui()
    o=u.prepare()
    u.update({"time":5,"time_length":10,"volume":100,"mute":False,"pause":"False"})
    print(o)
