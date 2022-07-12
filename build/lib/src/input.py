import asyncio
import os
import time

type=None
if os.name=="nt":
    import msvcrt
    type="nt"
if os.name=="posix":
    import readchar
    type="posix"
class input:
    def __init__(self,callback):
        self.callback=callback
        self.stop=False
    def start(self):
        asyncio.get_event_loop().run_in_executor(None,self.checker)
        return self
    def checker(self):
        if type=="nt":
            while True:
                time.sleep(0.05)
                if self.stop:return
                char=msvcrt.getch()
                if char==b"\x00":
                    char=msvcrt.getch()
                    char={b";":"f1",b"<":"f2",b"=":"f3",b">":"f4",b"?":"f5",b"@":"f6",b"A":"f7",b"B":"f8",b"C":"f9",b"D":"f10",b"R":"T_0",b"S":"T_.",b"O":"T_1",b"P":"T_2",b"Q":"T_3",b"K":"T_4",b"M":"T_6",b"G":"T_7",b"H":"T_8",b"I":"T_9"}[char]
                if char==b"\xe0":
                    char=msvcrt.getch()
                    char={b"\x86":"f12",b"H":"UP",b"P":"DOWN",b"K":"LEFT",b"M":"RIGHT",b"R":"INS",b"S":"DEL",b"I":"PGUP",b"Q":"PGDN",b"G":"HOME",b"O":"END"}[char]
                if char==b"\x1b":
                    char="esc"
                if char==b"\x08":
                    char="backspace"
                self.callback(char)
                
        if type=="posix":
            special={
                b"\x1b[3~":("DEL",0),
                b"\x1b[5":("PGUP",1),
                b"\x1b[6":("PGDN",1),
                b"\x1b[H":("HOME",0),
                b"\x1b[F":("END",0),
                b"\x1b[A":("UP",0),
                b"\x1b[B":("DOWN",0),
                b"\x1b[C":("RIGHT",0),
                b"\x1b[D":("LEFT",0),
                b"\x1b\x1b":("esc",0),
            }
            while True:
                time.sleep(0.1)
                if self.stop:return
                key = readchar.readkey().encode("utf-8")
                if key==b"\x1bO":
                    key={b"P":"f1",b"Q":"f2",b"R":"f3",b"S":"f4"}[readchar.readkey().encode("utf-8")]
                if key==b"\x1b[1":
                    key={b"5":"f5",b"7":"f6",b"8":"f7",b"9":"f8",b"0":"f9",b"1":"f10",b"4":"f12",b"~":"INS"}[readchar.readkey().encode("utf-8")]
                    if key[0]=="f":readchar.readkey()
                if key in special:
                    for _ in range(special[key][1]):readchar.readkey()
                    key=special[key][0]
                self.callback(key)

if __name__=="__main__":
    input(print).checker()