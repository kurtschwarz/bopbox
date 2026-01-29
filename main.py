import uasyncio

from bopbox import bopbox
from bopbox.services import logger


def main() -> None:
    bop = bopbox.BopBox(debug=True)

    try:
        uasyncio.run(bop.run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            uasyncio.run(bop.shutdown())
        except Exception as e:
            print(f"Shutdown Error: {e}")


main()
