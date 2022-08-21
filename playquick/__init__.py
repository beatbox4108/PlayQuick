try:import pyaudio
except ImportError:
    print("I'm sorry, but pyaudio (An audio library) is missing.")
    print("If you are using Windows,please try to run")
    print("\t> pip3 install pipwin")
    print("\t> pipwin install pyaudio")
    print("If you are using Debian/Ubuntu,please try to run")
    print("\t> sudo apt install python3-pyaudio")
    print("If you are using Redhat/CentOS,please try to run")
    print("\t> sudo dnf install pyaudio") 
    print("\t\tor,")
    print("\t> sudo yum install pyaudio") 
from . import app,commandline,data,input,player,stream,ui,__main__,localization
