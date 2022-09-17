import pathlib
import typing
from bs4 import BeautifulSoup
import bs4

class reader:
    def __init__(self,path) -> None:
        self.path=path
        self.title:str=None
        self.author:str=None
        self.files:typing.List[str,pathlib.Path]=None
        self.meta:typing.List[typing.Tuple[str,str]]
class wpl_reader(reader):
    def __init__(self, path) -> None:
        super().__init__(path)
        with open(path,encoding="utf-8")as f:
            soup=BeautifulSoup(f.read(),"xml")
        meta=[(e.get("name"),e.get("content"))for e in soup.find_all("meta")]
        head=soup.find("head")
        title=head.find("title")
        author=head.find("author")
        files=[((pathlib.Path(path).parent)/e.get("src")).resolve() for e in soup.find_all("media")]
        #print(meta,head,title,author,files)
        self.path=path
        self.files=files
        self.meta=meta
        self.title=title.string
        self.author=author.string 
class m3u_reader(reader):
    def __init__(self, path) -> None:
        super().__init__(path)
        with open(path,encoding="utf-8")as f:
            lines=f.readlines()
        self.path=path
        self.files=[((pathlib.Path(path).parent)/l.rstrip("\n")).resolve() for l in lines if (False if l=="" else l[0]!="#")]
        self.meta=None
        self.title=pathlib.Path(path).name
        self.author=None

if __name__=="__main__":
    wpl_reader('e:\Musics\Playlists\お気に入り - 森羅万象.wpl')
    m3u_reader('e:\Musics\Playlists\プレイリスト.m3u')
        
        