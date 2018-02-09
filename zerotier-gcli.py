#!/bin/env python3

"""
 Created by TyanBoot on 2018/2/8
 Tyan <tyanboot@outlook.com>

"""

import datetime
import json
import re
import sqlite3
import string
from curses.textpad import *

import requests

COLOR_TITLE = 1
COLOR_HEAD = 2
COLOR_ITEM = 3
COLOR_SELECTED = 4

with open("/var/lib/zerotier-one/authtoken.secret", "r") as f:
    headers = {
        "X-ZT1-Auth": f.read()
    }

db = sqlite3.connect("/var/lib/zerotier-one/networks.sqlite3")

with db:
    db.execute("""
    CREATE TABLE IF NOT EXISTS networks
    (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      name       TEXT,
      network_id TEXT,
      type       TEXT,
      ip         TEXT
    );""")


def get_saved_networks():
    networks = []
    with db:
        cur = db.execute("""SELECT * FROM networks;""")
        data = cur.fetchall()
        for net in data:
            networks.append(
                {
                    "name": net[1],
                    "nwid": net[2],
                    "type": net[3],
                    "status": "LEFT",
                    "assignedAddresses": json.loads(net[4])
                }
            )

    return networks


def update_saved_networks(nw):
    with db:
        cur = db.execute("SELECT id FROM main.networks WHERE network_id = ?;", (nw["nwid"],))
        data = cur.fetchone()
        if data:
            db.execute("UPDATE main.networks SET main.networks.name = ?, main.networks.type = ?,"
                       "main.networks.ip = ?",
                       (nw["name"], nw["type"], json.dumps(nw["assignedAddresses"])))
        else:
            db.execute("INSERT INTO main.networks (name,network_id, type, ip) VALUES (?,?,?,?)",
                       (nw["name"], nw["nwid"], nw["type"], json.dumps(nw["assignedAddresses"])))


def remove_saved_networks(nwid):
    with db:
        db.execute("DELETE FROM main.networks WHERE main.networks.network_id = ?", (nwid,))


def merge_networks(nw1, nw2):
    nwids = [nw["nwid"] for nw in nw1]

    for nw in nw2:
        if nw["nwid"] not in nwids:
            nw1.append(nw)
    return nw1


def get_status():
    try:
        rep = requests.get("http://127.0.0.1:9993/status", headers=headers)
        return rep.json()
    except:
        return {}


def get_networks():
    saved_networks = get_saved_networks()
    try:
        rep = requests.get("http://127.0.0.1:9993/network", headers=headers)
        nws = merge_networks(rep.json(), saved_networks)
        return nws
    except:
        return []


def join_networks(nid):
    remove_saved_networks(nid)
    rep = requests.post("http://127.0.0.1:9993/network/{0}".format(nid), headers=headers)
    return rep.json()


def leave_networks(nid):
    nw_info = requests.get("http://127.0.0.1:9993/network/{0}".format(nid), headers=headers).json()
    update_saved_networks(nw_info)

    rep = requests.delete("http://127.0.0.1:9993/network/{0}".format(nid), headers=headers)
    return rep.json()


def get_peers():
    rep = requests.get("http://127.0.0.1:9993/peer", headers=headers)
    return rep.json()


def count_chinese(n):
    n = list(n)
    stl = 0
    for x in n:
        if x not in string.printable:
            stl += 1
    return stl


def inner(stdscr):
    if curses.can_change_color():
        try:
            # curses.init_color(curses.COLOR_BLACK, 180, 211, 207)
            curses.init_color(curses.COLOR_WHITE, 1000, 1000, 1000)
            curses.init_color(curses.COLOR_RED, 1000, 0, 0)
            # color for selected
            curses.init_color(10, 0, 666, 666)

            curses.init_pair(COLOR_SELECTED, curses.COLOR_BLACK, 10)
        except:
            curses.init_pair(COLOR_SELECTED, curses.COLOR_BLACK, curses.COLOR_CYAN)
    else:
        curses.init_pair(COLOR_SELECTED, curses.COLOR_BLACK, curses.COLOR_CYAN)

    curses.use_default_colors()
    curses.init_pair(COLOR_TITLE, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(COLOR_HEAD, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(COLOR_ITEM, curses.COLOR_WHITE, -1)

    # hide cursor
    curses.curs_set(0)

    curses.halfdelay(1)

    # get node status
    status = None

    maxY, maxX = stdscr.getmaxyx()

    title_win = curses.newwin(2, maxX, 0, 0)
    items_win = curses.newwin(maxY - 6, maxX, 2, 0)
    bottom_win = curses.newwin(2, maxX, maxY - 3, 0)

    # current select index
    current_select = 0
    max_item = 0

    items = []

    def draw_title():
        nonlocal status
        status = get_status()
        title_win.erase()
        title_text = "{0} - {1} - {2}".format(
            status.get("address", ""),
            "Online" if status.get("online", None) else "Offline",
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ).center(maxX)

        title_win.addstr(0, 0, title_text,
                         curses.color_pair(COLOR_TITLE))
        title_win.refresh()

    def draw_network():
        nonlocal items
        nonlocal max_item

        items_win.resize(maxY - 6, maxX)

        items_win.erase()
        items_win.border()

        # id | name | status | private | dev | mtu | ipv4 | ipv6 |
        title_text = "{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}".format(
            "Network id".center(16),
            "Name".center(16),
            "Status".center(15),
            "Type".center(9),
            "Device".center(8),
            "Mtu".center(6),
            "IPv4".center(20),
            "IPv6".center(20)
        ).ljust(maxX - 2)

        items_win.addstr(1, 1, title_text, curses.color_pair(COLOR_HEAD))

        items = get_networks()
        max_item = len(items)

        for index, net in enumerate(items):
            ipv4 = ""
            ipv6 = ""

            ips = net.get("assignedAddresses", None)
            if ips:
                # just display one for each
                for ip in ips:
                    if re.search("^(\d+(\.|)){4}(/\d+)?", ip):
                        ipv4 = ip
                    else:
                        ipv6 = ip

            line = "{0}|{1}|{2}|{3}|{4}|{5}|{6}|{7}".format(
                net["nwid"].center(16),
                net["name"].center(16 - count_chinese(net["name"])),
                net.get("status", "").center(15),
                net["type"].center(9),
                net.get("portDeviceName", "").center(8),
                str(net.get("mtu", "")).center(6),
                ipv4.center(20),
                ipv6.center(20)
            )
            line = line.ljust(maxX - count_chinese(line) - 2)
            color = curses.color_pair(COLOR_SELECTED) if index == current_select else curses.color_pair(COLOR_ITEM)

            items_win.addstr(index + 2, 1, line, color)

        items_win.refresh()

    def draw_bottom():
        bottom_win.mvwin(maxY - 3, 0)

        bottom_win.erase()
        bottom_win.addstr(
            "[ Q - Quit ] [ J - Join ] [ R - Rejoin ]".center(
                maxX - 1))
        bottom_win.addstr(1, 0, "[ L - Leave ] [ D - Delete ] [ P - Peers ]".center(maxX - 1))

        bottom_win.refresh()
        pass

    def draw_peers():
        nonlocal items
        nonlocal max_item

        items_win.resize(maxY - 6, maxX)

        items_win.erase()
        items_win.border()

        # node id | latency | role | address | linkQuality
        title_text = "{0}|{1}|{2}|{3}|{4}".format(
            "Node id".center(12),
            "Latency".center(6),
            "Role".center(8),
            "Path".center(32),
            "LinkQuality".center(4),
        ).ljust(maxX - 2)

        items_win.addstr(1, 1, title_text, curses.color_pair(COLOR_HEAD))
        items = get_peers()

        for index, peer in enumerate(items):
            ip = ""
            quality = 0
            if peer["paths"]:
                path = peer["paths"][0]
                ip = path.get("address", "")
                quality = path.get("linkQuality", -1)
            line = "{0}|{1}|{2}|{3}|{4}".format(
                peer["address"].center(12),
                str(peer["latency"]).center(6),
                peer["role"].center(8),
                ip.center(32),
                str(quality).center(4)
            )
            items_win.addstr(index + 2, 1, line, curses.color_pair(COLOR_ITEM))
        items_win.refresh()

    while True:
        maxY, maxX = stdscr.getmaxyx()

        # stdscr.refresh()
        draw_title()
        draw_network()
        draw_bottom()

        key = stdscr.getch()

        if key == ord("q"):
            curses.endwin()
            break
        elif key == curses.KEY_RESIZE:
            stdscr.erase()
        elif key == curses.KEY_UP:
            current_select -= 1
            if current_select < 0:
                current_select = 0
        elif key == curses.KEY_DOWN:
            current_select += 1
            if not current_select < max_item:
                current_select = max_item - 1
        elif key in [ord("j"), ord("J")]:
            curses.curs_set(1)
            bottom_win.erase()
            bottom_win.refresh()

            edit_win = curses.newwin(1, 40, maxY - 3, 57)
            bottom_win.erase()

            bottom_win.addstr(0, 40, "Enter network id: ")
            bottom_win.refresh()

            box = Textbox(edit_win, insert_mode=True)
            box.edit()
            nwid = box.gather().strip()

            curses.curs_set(0)
            if len(nwid) == 16:
                join_networks(nwid)

        elif key in [ord("l"), ord("L")]:
            nwid = items[current_select]["nwid"]
            leave_networks(nwid)
        elif key in [ord("r"), ord("R")]:
            join_networks(items[current_select]["nwid"])
        elif key in [ord("d"), ord("D")]:
            remove_saved_networks(items[current_select]["nwid"])
        elif key in [ord("p"), ord("P")]:
            while True:
                draw_peers()
                draw_title()
                key = stdscr.getch()
                if key in [ord("q"), ord("Q")]:
                    break


if __name__ == '__main__':
    curses.wrapper(inner)
