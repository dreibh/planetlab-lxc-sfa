#!/usr/bin/env python3

# sfi -- slice-based facility interface

import sys
from sfa.client.sfi import Sfi

if __name__ == "__main__":
    sys.exit(Sfi().main())
