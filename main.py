import sys
import uasyncio

from bopbox import bopbox


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
            sys.print_exception(e)


main()
