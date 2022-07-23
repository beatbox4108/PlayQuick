"""
data
====
data is classes of objects.
"""

import asyncio
from io import TextIOWrapper
import json
import math
import pathlib
import typing
import pydub.utils
import rich
import rich.table


avaliable_codecs=("wav","mp2","mp3","m4a","ogg","opus","flac")

avaliable_languages=(
    "Chinese Simplified",
    "Chinese Traditional",
    "Dutch",
    "English, India",
    "English",
    "Finnish",
    "French",
    "German",
    "Hebrew",
    "Hindi",
    "Italian",
    "Japanese",
    "Korean",
    "Portuguese, Brazilian",
    "Portuguese",
    "Romanian",
    "Russian",
    "Spanish",
    "Swedish",
    "Ukrainian",
)


def convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return "%s %s" % (s, size_name[i])


class sampleClip:
    def __init__(self,sample:bytes,time:typing.Optional[int]=...,*,CHUNK:typing.Optional[int]=...) -> None:
        self.time:typing.Union(None,int)=time
        self.sample:bytes=sample
        self.CHUNK:typing.Optional[int]=CHUNK


class song:
    def __init__(self,path) -> None:
        self._path=pathlib.Path(path)
        self.path=str(self._path),self._path.suffix.lstrip(".")
        self.info={}
        self.title="?"
        self.artist="?"
        self.album="?"
    def read(self):
        try:
            self.info:dict=pydub.utils.mediainfo(self._path)["TAG"]
            self.title=self._path.name if self.info.get("title") is None else self.info.get("title")
            self.artist="?" if self.info.get("artist") is None else self.info.get("artist")
            self.album="?" if self.info.get("album") is None else self.info.get("album")
        except:pass
        

class selection:
    def __init__(self,x:int=None,y:int=None) -> None:
        if x is None or y is None:
            self.x=x
            self.y=y
            self.none=True
            return
        self.none=False
        self.x,self.y=sorted([x,y])
    def clip_iterable(self,iterable:typing.Iterable):
        return tuple(iterable)[self.x:self.y]
    def pop_iterable(self,iterable:typing.List):
        return [*iterable[:self.x],*iterable[self.y+1:]]
    def is_none(self):return self.none
    def __contains__(self,index) -> bool:return self.is_in(index)
    def is_in(self,index) -> bool:
        if self.is_none():
            if index in (self.x,self.y):return True
            return False
        return self.x <= index <= self.y

    
class playlist:
    def __init__(self,version=...) -> None:
        self.list=None
        self.version=...
    def open(self,io:TextIOWrapper):
        data=json.load(io.read())
        data["version"]=self.version
        


class queue:
    def __init__(self) -> None:
        self._playing:typing.Union[int,None]=None
        self.queue:typing.List[song]=[]
    def load(self,loop:asyncio.AbstractEventLoop):
        for i in self.queue:
            if i.info=={}:loop.run_in_executor(None,i.read)
    @property
    def playing(self):return self._playing
    @playing.setter
    def playing(self,val):
        self._playing=None if val is None else (0 if val<0 else len(self.queue)-1 if val>len(self.queue)-1 else val)
    def append(self,*args):
        for f in args:
            self.queue.append(f)
    def insert(self,index,*args):
        for f in args[::-1]:
            self.queue.insert(index,f)
    def clear(self):self.queue=[]
    def clipping(self,selection:selection):
        return selection.clip_iterable(self.queue)
    def remove_items(self,selection:typing.Union[selection,int]):
        if selection is int:return self.queue.pop(selection)
        self.queue=selection.pop_iterable(self.queue)


    def __len__(self):return len(self.queue)

class propertydata:
    def __init__(self) -> None:
        self.table=rich.table.Table(expand=True)
    def read_from_song(self,song:song,*,include_pathdata=True):
        if song.info=={}:
            song.read()
        self.table.add_row("title",song.title)
        self.table.add_row("artist",song.artist)
        self.table.add_row("album",song.album)
        self.table.add_row("description",song.info.get("description"))
        if include_pathdata:
            self.table.add_row("type",song.path[1])
            self.table.add_row("path",song.path[0])
        return self
    def read_from_file(self,path:typing.Union[pathlib.Path,str]):
        path:pathlib.Path=pathlib.Path(path)
        if path.is_symlink():
            self.table.add_row("filetype","Link")
            self.table.add_row("path",str(path))
        elif path.is_dir():
            self.table.add_row("filetype","Directory")
            #self.table.add_row("items",len(list(path.glob("./*"))))
            #self.table.add_row("sub-directories",len(list(path.glob("./*/"))))
            self.table.add_row("path",str(path))
        if path.is_file():
            if path.suffix.lstrip(".") in avaliable_codecs:
                self.table.add_row("filetype","Audiofile (Openable)")
                self.table.add_row("path",str(path))
                self.table.add_row("ext",path.suffix)
                self.table.add_row("size",convert_size(path.stat().st_size))
                self.read_from_song(song(path))
            else:
                self.table.add_row("filetype","File")
                self.table.add_row("path",str(path))
                self.table.add_row("ext",path.suffix)
                self.table.add_row("size",convert_size(path.stat().st_size))
        return self
