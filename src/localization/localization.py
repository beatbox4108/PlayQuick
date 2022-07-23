import json
import typing
import pathlib


class Locarization:
    def __init__(self)->None:
        self.data:typing.Union[dict,ellipsis]=...
    @classmethod
    def read(cls,lang=...,*,file=...):
        self=cls()
        if lang is ...:
            if file is ...:lang="English"
            else:
                with open(file,"r",encoding="utf-8") as f:self.data=json.load(f)
                return self
        with open((pathlib.Path(__file__).parent)/"i18n"/f"{lang}.json","r",encoding="utf-8") as f:self.data=json.load(f)
        return self
    def get(self,name):
        if self.data is ...:return name
        else:return name if self.data.get(name) is None else self.data.get(name)
    def is_readable(self):return self.data is ...