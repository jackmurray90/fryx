# Trade API

Trade API is an open source cryptocurrency exchange.

There is currently an implementation running at fryx.finance.

## Instructions

To get it up and running, first create a virtual environment and install
requirements.txt.

Then install postgresql, bitcoin, and monero.

Create a new database and configure postgres, bitcoin, and monero settings in env.py.

Sync both blockchains and run setup.py to setup the databases.

Then run the server using flask.

In the background, run blockchain\_monitor.py
