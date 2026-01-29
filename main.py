import sys
import uasyncio

from bopbox import bopbox
from bopbox.services import logger


def main() -> None:
    bop = bopbox.BopBox()

    try:
        uasyncio.run(bop.run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        sys.print_exception(e)
    finally:
        try:
            uasyncio.run(bop.shutdown())
        except Exception as e:
            print(f"Shutdown Error: {e}")


main()
