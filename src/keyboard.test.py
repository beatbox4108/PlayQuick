from asyncore import read
import readchar

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
    key = readchar.readkey().encode("utf-8")
    if key==b"q":break
    if key==b"\x1bO":
        key={b"P":"f1",b"Q":"f2",b"R":"f3",b"S":"f4"}[readchar.readkey().encode("utf-8")]
    if key==b"\x1b[1":
        key={b"5":"f5",b"7":"f6",b"8":"f7",b"9":"f8",b"0":"f9",b"1":"f10",b"4":"f12",b"~":"INS"}[readchar.readkey().encode("utf-8")]
        if key[0]=="f":readchar.readkey()
    if key in special:
        for _ in range(special[key][1]):readchar.readkey()
        key=special[key][0]
    print(key)