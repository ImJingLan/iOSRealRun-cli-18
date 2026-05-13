import signal
import logging
import coloredlogs
import os
import asyncio

from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

from init import init
from init import tunnel
from init import route

import run

import config


debug = os.environ.get("DEBUG", False)

coloredlogs.install(level=logging.INFO)
logging.getLogger('wintun').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('quic').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('zeroconf').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('parso.cache').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('parso.cache.pickle').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('parso.python.diff').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('humanfriendly.prompts').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('blib2to3.pgen2.driver').setLevel(logging.DEBUG if debug else logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.DEBUG if debug else logging.WARNING)


async def _async_main():
    logger = logging.getLogger(__name__)
    coloredlogs.install(level=logging.INFO)
    logger.setLevel(logging.INFO)
    if debug:
        logger.setLevel(logging.DEBUG)
        coloredlogs.install(level=logging.DEBUG)

    await init.init()
    logger.info("init done")

    logger.info("starting tunnel")
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        process, address, port = tunnel.tunnel()
    except RuntimeError as exc:
        logger.error("failed to start tunnel: %s", exc)
        print(f"启动隧道失败：{exc}")
        return
    finally:
        signal.signal(signal.SIGINT, original_sigint_handler)
    logger.info("tunnel started")
    try:
        logger.debug(f"tunnel address: {address}, port: {port}")

        loc = route.get_route()
        logger.info(f"got route from {config.config.routeConfig}")

        async with RemoteServiceDiscoveryService((address, port)) as rsd:
            async with DvtProvider(rsd) as dvt:
                async with LocationSimulation(dvt) as loc_sim:
                    try:
                        print(f"已开始模拟跑步，速度大约为 {config.config.v} m/s")
                        print("会无限循环，按 Ctrl+C 退出")
                        print("请勿直接关闭窗口，否则无法还原正常定位")
                        await run.run(loc_sim, loc, config.config.v)
                    except KeyboardInterrupt:
                        logger.debug("get KeyboardInterrupt (inner)")
                        logger.debug(f"Is process alive? {process.is_alive()}")
                    finally:
                        logger.debug(f"Is process alive? {process.is_alive()}")
                        logger.debug("Start to clear location")
                        await loc_sim.clear()
                        logger.info("Location cleared")

    except KeyboardInterrupt:
        logger.debug("get KeyboardInterrupt (outer)")
    finally:
        logger.debug(f"Is process alive? {process.is_alive()}")
        logger.debug("terminating tunnel process")
        process.terminate()
        logger.info("tunnel process terminated")
        print("Bye")


def main():
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
