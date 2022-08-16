import argparse
import asyncio
import pathlib
import sys

import rich
import rich.columns

from . import localization

def main():
    console=rich.console.Console()
    parser=argparse.ArgumentParser("PlayQuick",description="Simple media player that has UI and works on the console.")
    parser.add_argument("-f","--file",help="Set filepath.",type=str,nargs="+")
    parser.add_argument("-v","--volume",help="Set volume.",type=int,default=100)
    parser.add_argument(
        "-r","--repeat","--repeat-mode",
        help="Set repeat-mode.\n\
            No-repeat: 0\n\
            Repeat-queue: 1\n\
            No-repeat: 2",
        type=int,
        choices=[0,1,2])
    parser.add_argument("--dir","--open-with",help="Open directory on browser UI. (Only avaliable on UI.)",type=str,default=pathlib.Path.home())
    parser.add_argument("--list","--list-codecs",help="list supported codecs.",action="store_true")
    parser.add_argument("-l","--lang",help="Select language. -l list to show avaliable languages.",type=str,default="English")
    subparser=parser.add_subparsers(dest="subcommand")
    #noui=subparser.add_parser("noui",description="Disable UI.",)
    args=parser.parse_args()

    import data

    if args.lang=="list":
        console.rule("Avaliable languages for PlayQuick")
        console.print(rich.columns.Columns(data.avaliable_languages))
        console.rule()
        console.print("Let's [link=https://crowdin.com/project/playquick]contribute our project translation[/]!")
        sys.exit()
    if not args.lang in data.avaliable_languages:
        lang="English"
        console.log(f"Skipping UNKNOWN language \"{args.lang}\"")
    else:lang=args.lang
    i18n=localization.localization.Locarization.read(lang)
    
    if args.list:
        console.rule("Avaliable codecs on PlayQuick")
        console.print(rich.columns.Columns(data.avaliable_codecs))
        sys.exit()
    from app import app
    a=app(console,browser_dir=args.dir,localization=i18n)#,ui_mode=args.subcommand!="noui")
    a.open(args.volume)
    if args.repeat == 0:a.repeat=0
    elif args.repeat == 1:a.repeat=1
    if args.repeat == 2:a.repeat=2
    
    if args.file is not None:
        for i in args.file:
            a.queue.append(data.song(i))
        a.stream.pause=False
    try:
        a.mainloop()
    except KeyboardInterrupt:pass
    except Exception as e:
        rich.console.Console().print_exception()
    a.stream.close()
    sys.exit()
