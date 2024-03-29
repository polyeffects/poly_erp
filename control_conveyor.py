# if we've got a board in the last 6 seconds, wait to make it positive
import sys, time, subprocess
last_board = 0
time_between_boards = 90

def toggle_conveyor():
    global last_board
    # print("in toggling conveyor")
    while last_board + time_between_boards > time.time():
        time.sleep(0.1)
    # toggle_conveyor
    print("toggling conveyor")
    subprocess.run(["/git_repos/poly_erp/posdamio", "-o", "152=1", "192.168.88.250"], stdout = subprocess.DEVNULL)
    subprocess.run(["/git_repos/poly_erp/posdamio", "-o", "151=1", "192.168.88.250"], stdout = subprocess.DEVNULL)
    last_board = time.time()
    time.sleep(5)
    subprocess.run(["/git_repos/poly_erp/posdamio", "-o", "152=0", "192.168.88.250"], stdout = subprocess.DEVNULL)
    subprocess.run(["/git_repos/poly_erp/posdamio", "-o", "151=0", "192.168.88.250"], stdout = subprocess.DEVNULL)
