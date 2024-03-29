import os,time
#import ioctl_opt
import fcntl,threading,queue
import ctypes
import struct
import sys
import action_table
import json

_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRMASK = (1 << _IOC_NRBITS) - 1
_IOC_TYPEMASK = (1 << _IOC_TYPEBITS) - 1
_IOC_SIZEMASK = (1 << _IOC_SIZEBITS) - 1
_IOC_DIRMASK = (1 << _IOC_DIRBITS) - 1

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

IOC_NONE = 0
IOC_WRITE = 1
IOC_READ = 2

def IOC(dir, type, nr, size):
    assert dir <= _IOC_DIRMASK, dir
    assert type <= _IOC_TYPEMASK, type
    assert nr <= _IOC_NRMASK, nr
    assert size <= _IOC_SIZEMASK, size
    return (dir << _IOC_DIRSHIFT) | (type << _IOC_TYPESHIFT) | (nr << _IOC_NRSHIFT) | (size << _IOC_SIZESHIFT)

def IOC_TYPECHECK(t):
    result = ctypes.sizeof(t)
    assert result <= _IOC_SIZEMASK, result
    return result

def IO(type, nr):
    return IOC(IOC_NONE, type, nr, 0)

def IOR(type, nr, size):
    return IOC(IOC_READ, type, nr, IOC_TYPECHECK(size))

def IOW(type, nr, size):
    return IOC(IOC_WRITE, type, nr, IOC_TYPECHECK(size))

def IOWR(type, nr, size):
    return IOC(IOC_READ | IOC_WRITE, type, nr, IOC_TYPECHECK(size))

def IOC_DIR(nr):
    return (nr >> _IOC_DIRSHIFT) & _IOC_DIRMASK

def IOC_TYPE(nr):
    return (nr >> _IOC_TYPESHIFT) & _IOC_TYPEMASK

def IOC_NR(nr):
    return (nr >> _IOC_NRSHIFT) & _IOC_NRMASK

def IOC_SIZE(nr):
    return (nr >> _IOC_SIZESHIFT) & _IOC_SIZEMASK

IOC_IN = IOC_WRITE << _IOC_DIRSHIFT
IOC_OUT = IOC_READ << _IOC_DIRSHIFT
IOC_INOUT = (IOC_WRITE | IOC_READ) << _IOC_DIRSHIFT
IOCSIZE_MASK = _IOC_SIZEMASK << _IOC_SIZESHIFT
IOCSIZE_SHIFT = _IOC_SIZESHIFT

if False and __name__ == '__main__':
    print('Sanity checks...')
    # hid.h
    HID_MAX_DESCRIPTOR_SIZE = 4096

    # hidraw.h
    class hidraw_report_descriptor(ctypes.Structure):
        _fields_ = [
            ('size', ctypes.c_uint),
            ('value', ctypes.c_ubyte * HID_MAX_DESCRIPTOR_SIZE),
        ]

    class hidraw_devinfo(ctypes.Structure):
        _fields_ = [
            ('bustype', ctypes.c_uint),
            ('vendor', ctypes.c_short),
            ('product', ctypes.c_short),
        ]

    HIDIOCGRDESCSIZE = IOR(ord('H'), 0x01, ctypes.c_int)
    HIDIOCGRDESC = IOR(ord('H'), 0x02, hidraw_report_descriptor)
    HIDIOCGRAWINFO = IOR(ord('H'), 0x03, hidraw_devinfo)
    HIDIOCGRAWNAME = lambda len: IOC(IOC_READ, ord('H'), 0x04, len)
    HIDIOCGRAWPHYS = lambda len: IOC(IOC_READ, ord('H'), 0x05, len)
    HIDIOCSFEATURE = lambda len: IOC(IOC_WRITE|IOC_READ, ord('H'), 0x06, len)
    HIDIOCGFEATURE = lambda len: IOC(IOC_WRITE|IOC_READ, ord('H'), 0x07, len)
    HIDIOCGRAWNAME(0)
    HIDIOCGRAWPHYS(1)
    HIDIOCGRAWPHYS(_IOC_SIZEMASK)
    HIDIOCGFEATURE(_IOC_SIZEMASK)

class USBBarcodeScanner(object):
    def __init__(self,vidPidList=[('011c','0581')]):
        self.device=self.findDevice(vidPidList)
        if not self.device:
            raise Exception("Scanner not found")
        self.queue=queue.Queue()
        self.readThread=threading.Thread(target=self.readerThread)
        self.readThread.daemon=True
        self.readThread.start()


    def readerThread(self):
        device=self.device
        try:
            fd = open(device, 'rb')
        except FileNotFoundError:
            print("No such scanner device, is it connected?")
            raise
        except PermissionError:
            print("Insufficent permission to read, run me as root!")
            raise

        # from input-event-codes.h
        # type can be EV_SYN, EV_KEY or EV_MSC
        EV_KEY = 1
        KEY_DOWN = 1

        # from input.h:
        EVIOCGNAME = lambda len: IOC(IOC_READ, ord('E'), 0x06, len)
        EVIOCGRAB = lambda len: IOW(ord('E'), 0x90, ctypes.c_int)
        name = ctypes.create_string_buffer(256)

        # also from input.h
        event_format = "llHHI"
        event_size = struct.calcsize(event_format)

        fcntl.ioctl(fd, EVIOCGNAME(256), name, True)
        #print("Device calls itself: " + name.value.decode('UTF-8'))

        fcntl.ioctl(fd, EVIOCGRAB(1), True)

        e_sec = "" # unix epoch second
        e_usec = "" # unix epoch microsecond
        e_type = "" # EV_SYN, EV_KEY, EV_MSC etc
        e_code = "" # keycode, see http://www.comptechdoc.org/os/linux/howlinuxworks/linux_hlkeycodes.html
        e_val = "" # keydown = 1, keyup = 0

        # !! This may not be exactly right!!!!!!
        MAPU=" "+chr(27)+"1234567890-=  qwertyuiop[]"+chr(13)+" asdfghjkl;'` \\zxcvbnm,./    "
        MAPS=" "+chr(27)+"!@#$%^&*()_+  QWERTYUIOP{}"+chr(13)+" ASDFGHJKL:\"` \\ZXCVBNM,./    "
        kmap=MAPU
        line=""
        while True:
            byte = fd.read(event_size)
            e_sec, e_usec, e_type, e_code, e_val = struct.unpack(event_format, byte)
            if e_type == EV_KEY:
                if e_code==42 or e_code==54: #shifts
                    shift=e_val
                    kmap=MAPU if not shift else MAPS
                    #print(shift)
                elif e_val == KEY_DOWN:
                    # Ugly mapping of number keys to their values
                    ch=0
                    if e_code<len(kmap):
                        ch=kmap[e_code]
                        if ch==chr(13):
                            self.queue.put(line)
                            line=""
                        else:
                            line+=ch
    def readline(self):
        if self.queue.empty():
            return None
        return self.queue.get()

    def findDevice(self,vidPidList):
        import pyudev
        ctx = pyudev.Context()
        allDev = ctx.list_devices(subsystem='input', ID_BUS='usb')

        foundDev = []
        print("Found the following USB input devices: \n")
        count = 0
        for dev in allDev:
            if dev.device_node is not None:
                count += 1
                foundDev.append(dev.device_node)
                # print(str(count), end =". ")
                # print(dev['ID_SERIAL'], end=" ") # e.g. Logitech_HID_compliant_keyboard
                # print("device node", dev.device_node) # e.g. /dev/input/event/7
                # print("vendor id", dev['ID_VENDOR_ID']) # e.g. 046d
                # print("model id", dev['ID_MODEL_ID']) # e.g. c30e
                # print("before for")
                vid=dev.get('ID_VENDOR_ID')
                pid=dev.get('ID_MODEL_ID')
                for p,v in vidPidList:
                    print( vid,v,pid,p)
                    if vid==v and pid==p:
                        return dev.device_node
        return None

if __name__ == '__main__':
    u=USBBarcodeScanner()
    while True:
        l=u.readline()
        if l:
            print(l)
            # if we start with PA: were are poly product code
            # eg PA:v:269
            if l.startswith("PA:"):
                pa, part, serial = l.split(":")
                if part == "v":
                    part = 249
                else:
                    part = int(part)
                action_table.add_unit_to_current_shipment(part, serial)
            else:
                try:
                    action_data = json.loads(l)
                    if "action" in action_data:
                        print("action matched", action_data)
                        action_table.barcode_actions[action_data["action"]](action_data)
                    # spawn thread to process each action, need a table of actions and functions here
                    # print label
                    # start task
                    # complete task
                    # on print label, create new completed unit, 
                    # tested unit marked as packed or completed assembly consumes tested unit
                except Exception as err:
                    print(f"Unexpected {err=}, {type(err)=}")


        else:
            time.sleep(0.1)

