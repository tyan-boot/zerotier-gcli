# ZeroTier CLI using curses

# Introduction

This is an interactive zerotier cli. It requires `curses` and `requests`. Developed for linux, but __may__ work for Windows.

![img](https://i.loli.net/2018/02/09/5a7d55f4519b7.png)

# Usage

| Key | Function |
| --- | --- |
| Q | Quit |
| J | Join a network |
| L | Leave selected network, but don't remove from database |
| D | Delete a network from database |
| R | Rejoin a leaved network |
| P | List peers. Press Q to return to networks list |

__Notice__, When join a network, the textbox key binds:

| Key | Function |
| --- | --- |
| Ctrl-A | Go to left edge. |
| Ctrl-B | Cursor left. |
| Ctrl-D | Delete character under cursor. |
| Ctrl-E | Go to right edge. |
| Ctrl-F | Cursor right |
| Ctrl-H | Delete character backward. |