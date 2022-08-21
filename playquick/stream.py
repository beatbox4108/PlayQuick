import asyncio
import collections
import concurrent.futures
import threading

import pyaudio

from . import data,player


class stream:
    def __init__(self,volume:int=100) -> None:
        self.pyaudio=pyaudio.PyAudio()
        self.maxthreadqueue:int=25
        self._info=None
        self._timeinfo={}
        self.volume=volume
        self.pause=True
        self.mute=False
        self.getback=False
    def open(self,info):
        """Open stream. You don't need to run this if you aren't going to write stream yourself."""
        self.stream:pyaudio.Stream=self.pyaudio.open(**info,output=True)
        self._info={}
        return self
    def close(self):
        self._info={}
        self.stream=None
    def write(self,sample:data.sampleClip):
        self.stream.write(sample.sample)
        self._update_sample_count(sample.time,sample.CHUNK)
    async def play(self,player:player.player):
        info=player.get_info()
        info["format"]=self.pyaudio.get_format_from_width(info["format"])
        self.open(info)
        self.pool=concurrent.futures.ThreadPoolExecutor(1)
        self.getback=False
        self.timeline=0
        self._update_sample_count(0,player.CHUNK)
        while True:
            self._info=collections.ChainMap(self._timeinfo,player.mediainfo)
            sample=player.read(self.timeline,volume=0 if self.mute else self.volume)
            if sample is None:break
            if self.getback:break
            while True:
                if self.pool._work_queue.qsize() < self.maxthreadqueue:break
                await asyncio.sleep(0.1)
            while self.pause:await asyncio.sleep(0.1)
            self.pool.submit(self.write,sample)
            self.timeline+=1
            #print(f"samples:{self.timeline} queue:{self.pool._work_queue.qsize()} time:{self.timeline*sample.CHUNK/1000} time(info):{self._info['time']}",end="\r")
        self.close()
    def _update_sample_count(self,time,chunk):
        self._timeinfo["time"]=time*chunk/1000
    @property
    def info(self):return self._info

if __name__=="__main__":
    s=stream()
    s.volume=50
    p=player.advanced_player()
    p.load("./src/sample2.mp3","mp3")
    asyncio.run(s.play(p))
