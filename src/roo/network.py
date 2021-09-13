from typing import Optional, Union, Dict, cast

import requests
import logging

logger = logging.getLogger(__file__)


def session_with_proxy(proxy: Optional[Union[str, bool]]) -> requests.Session:
    logger.info(f"Creating session with proxy={proxy}")
    session = requests.Session()

    if proxy is None:
        # If no proxy info is specified, use the default session, which
        # also trusts the environment
        return session

    proxy_config: Dict[str, str]
    session.trust_env = False
    if proxy is False:
        proxy_config = {}
    else:
        proxy_config = {
            "http": cast(str, proxy),
            "https": cast(str, proxy)
        }

    session.proxies = proxy_config
    return session
