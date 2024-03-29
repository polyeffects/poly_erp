import os, sys
import time
import subprocess
import paho.mqtt.client as mqtt
import win32file, msvcrt

# def follow(thefile):
#     '''generator function that yields new lines in a file
#     '''
#     # seek the end of the file
#     thefile.seek(0, os.SEEK_END)
#     # start infinite loop
#     while True:
#         # read last line of file
#         line = thefile.readline() # sleep if file hasn't been updated
#         if not line:
#             time.sleep(0.2)
#             continue
#         yield line

def follow(bak_filename, client):
    current = open_file(bak_filename)
    bak_modified_time = os.stat(bak_filename).st_mtime
    current.seek(0, os.SEEK_END)
    where = current.tell()
    try:
        while True:
            if not current.closed:
                line = current.readline()
                where = current.tell()
                if line:  # Read a line
                    client.publish("pnp/luke", line)#publish
                else: # no new line, close file
                    current.close()
                    time.sleep(1)
            elif ((not bak_modified_time and os.path.exists(bak_filename)) or
                  (bak_modified_time and os.path.exists(bak_filename) and
                   os.stat(bak_filename).st_mtime != bak_modified_time))
                # print('[Debug] Detected new file')
                bak_modified_time = os.stat(bak_filename).st_mtime
                current = open_file(bak_filename)
                file_size = os.stat(bak_filename).st_size
                if where <= file_size: # new file, seek to start
                    print('[Debug] Detected new file')
                    where = 0
                current.seek(where)
            else:
                time.sleep(1)
    finally:
        # close the file
        if not current.closed:
            current.close()


def open_file(filename):
    # get an handle using win32 API, specifying the SHARED access!
    handle = win32file.CreateFile(filename,
                                  win32file.GENERIC_READ,
                                  win32file.FILE_SHARE_DELETE |
                                  win32file.FILE_SHARE_READ |
                                  win32file.FILE_SHARE_WRITE,
                                  None,
                                  win32file.OPEN_EXISTING,
                                  0,
                                  None)
    # detach the handle
    detached_handle = handle.Detach()
    # get a file descriptor associated to the handle\
    file_descriptor = msvcrt.open_osfhandle(detached_handle, os.O_RDONLY)
    # open the file descriptor
    f = os.fdopen(file_descriptor)

    return f

# def follow(self):
#     if not os.path.isfile(self.filename):
#         return False

#     current = self.open_file()
#     bak_modified_time = None
#     try:
#         while True:
#             line = current.readline().strip()
#             where = current.tell()
#             if line:  # Read a line
#                 if 'error' in line:  # If error found in line
#                     self.found = True
#                     print '[Debug] Found exception'
#                     break
#             elif self.stop:  # no new line and no new file. Stop reading if not stop
#                 print '[Debug] Stopping'
#                 break
#             elif ((not bak_modified_time and os.path.exists(self.bak_filename)) or
#                   (bak_modified_time and os.path.exists(self.bak_filename) and
#                    os.stat(self.bak_filename).st_mtime != bak_modified_time))
#                 print '[Debug] Detected new file'
#                 new = self.open_file()
#                 current.close()
#                 current = new
#                 bak_modified_time = os.stat(self.bak_filename).st_mtime
#             else:  # no new line and no new file and not stop. Sleep for a second
#                 print '[Debug] sleeping'
#                 current.seek(where)
#                 time.sleep(2)
#     finally:
#         # close the file
#         current.close()

# ts = 0
# while True:
#     mt = os.stat(r"C:\").st_mtime
#     if mt != ts:
#         # sync file
#         ts = mt
#         p = subprocess.Popen(r"C:\poly\copy_log.cmd", shell=True)
#         p.communicate()
#     time.sleep(5)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    if "broker" not in msg.topic:
        print(msg.topic+" "+str(msg.payload))

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
if __name__ == '__main__':
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("192.168.20.7", 1883, 60)
    client.loop_start()
    follow(r"C:\UPS 6.08.00\usos\log\USOS-LOG.htm", client)
    client.loop_stop()
