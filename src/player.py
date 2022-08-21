import pathlib
import typing

import numpy as np
import pyaudio
import pydub
import pydub.utils

import data


class player:
    def __init__(self):
        self.file=None
        self.CHUNK=16
        self._mediainfo={}
    def load(self,file:typing.Union[str,pathlib.Path],ext):
        mediainfo=pydub.utils.mediainfo(file)
        self._mediainfo=mediainfo["TAG"]
        self._mediainfo["time_length"]=float(mediainfo["duration"])
        self.file:pydub.AudioSegment=pydub.AudioSegment.from_file(file,ext)
    def read_sample(self,sample_count)-> typing.Union[pydub.AudioSegment,None]:
        return self.file[sample_count*self.CHUNK:(sample_count+1)*self.CHUNK] if self.duration>(sample_count*self.CHUNK) else None
    def read(self,sample_count,*args,**kwargs)->data.sampleClip:pass
    def play(self,stream):pass
    def __len__(self):return len(self.file)
    @property
    def duration(self) -> int:return len(self)
    def get_info(self):
        """returns audio info for pyaudio"""
        data={}
        data["rate"]=self.file.frame_rate
        data["channels"]=self.file.channels
        data["format"]=2
        return data
    @property
    def mediainfo(self):return self._mediainfo

class simple_player(player):
    def read(self,sample_count) -> data.sampleClip:return data.sampleClip(self.read_sample(sample_count).to_bytes,sample_count)
    async def play(self,stream):
        await stream.play(self)

class advanced_player(player):
    def read(self, sample_count, *args, volume=100, **kwargs) -> typing.Union[None,data.sampleClip]:
        sample:pydub.AudioSegment=self.read_sample(sample_count)
        if sample is None:return None
        sample=sample + pydub.utils.ratio_to_db(volume/100)
        return data.sampleClip(sample.raw_data,time=sample_count,CHUNK=self.CHUNK)
