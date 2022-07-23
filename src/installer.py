from pip._internal.operations import freeze
import os,sys
import subprocess
import rich
import rich.progress
from rich import print,console
def setup(con:console.Console=console.Console()):
    con.log("Installing external library.")
    with rich.progress.Progress() as progress:
        task1=progress.add_task("Checking your Operating System.",total=100)
        task2=progress.add_task("Installing external library.",total=None)
        ostype=os.name
        progress.update(task1,completed=100,description=f"Your OS is {ostype}")
        if ostype=="nt":
            progress.update(task2,description="Installing pipwin for installing library.")
            subprocess.call([sys.executable,"-m","pip","install","pipwin"],stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
            progress.update(task2,description="Installing pyaudio",total=100,completed=50)
            subprocess.call([sys.executable,"-m","pipwin","install","PyAudio"],stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
            progress.update(task2,description="Required library were installed successfly!",completed=100)
        else:
            progress.update(task2,description="Installing PyAudio.")
            try:
                subprocess.call(["sudo","apt","install","python3-pyaudio"],stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
            except:
                try:
                    subprocess.call(["sudo","yum","install","python3-pyaudio"],stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
                except:
                    try:
                        subprocess.call(["sudo","dnf","install","python3-pyaudio"],stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
                    except:
                        progress.update(task2)
                        con.log("Installition failed. Please install pyaudio manually.")
                        return False
            progress.update(task2,description="Successfly installed PyAudio!",completed=100)
    con.log("Successfly installed external library!")
    return True

def check(console:console.Console=console.Console()):
    try:
        import pyaudio
    except ImportError:
        console.bell()
        if setup(console):
            print("[magenta]Sorry,we have updated library. So, please restart PlayQuick.")
        console.bell()
        sys.exit(0)