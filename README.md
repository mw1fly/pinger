# Pinger

Description: Pings things and alerts when up/down 
Currently works on Computer A, needs tweaks for portability.

## Updates

Added portability tweaks, make sure you have Python venv installed on your host.

## ToDo
 
Add/Fix Logs
Add Handle Mass outage
Up/Down Filters
...

## Setup
- Requirements: Python 3
- python3.13-venv
- Run with:
  ```bash
  ./pinger.sh

```

## Errors
 - Try deleteing .venv  
 - Copy config.example.py to config.py
 - Delete ip_list.txt

⚙  Creating virtual environment...
The virtual environment was not created successfully because ensurepip is not
available.  On Debian/Ubuntu systems, you need to install the python3-venv
package using the following command.

    apt install python3.13-venv

You may need to use sudo with that command.  After installing the python3-venv
package, recreate your virtual environment.

---
