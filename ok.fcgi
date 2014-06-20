#!/usr/bin/env python3
from flipflop import WSGIServer
from ok import app

WSGIServer(app).run()
