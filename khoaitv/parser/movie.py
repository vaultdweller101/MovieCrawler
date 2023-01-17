
from typing import List, Optional, Any, Dict
from custom_request.request import AsyncRequest, AsyncSession
from utils.helper import inject_async_session
from khoaitv.config import Config
from bs4 import BeautifulSoup
import asyncio
import re

SWITCHER = {
    "Ngày phát hành ": "year",
    "Trạng thái": "status",
    "Thời lượng": "duration",
    "Thể loại": "genres",
    "Quốc gia": "country",
    "Diễn viên": "casts",
    "Đạo diễn": "directors"
}

class MovieParser:

    @classmethod
    @inject_async_session
    async def get_episodes_urls(self, url: str, content=None, retry=True, session = None, debug=False) -> List[str]:
        '''
        url: http://khoaitv.org/phim/shameless-season-10-mat-day-phan-10-13270

        URL has to be a watch button url
        '''
        if not content:
            content, _ = await AsyncRequest.get(url, delay=Config.REQUEST_DELAY, retry=True, session=session)

        html_parse = BeautifulSoup(content, "html.parser")
        try:
            ul = html_parse.find("div", class_="episode-film").find("ul")
            if ul:
                urls = [{li.find("a").text.strip(): li.find("a")["href"]} for li in ul.findAll("li")]
                return urls
            else: # non-episodic
                return [{"Full": url+"-tap-1"}]
        except Exception as e:
            if debug:
                print(f"get_episodes_urls(). Error: \n {repr(e)}")

        return []

    @classmethod
    @inject_async_session
    async def get_movie_info(self, url: str, content=None, session = None, debug=False) -> Optional[Dict[str, str]]:
        global SWITCHER

        try:
            if not content:
                content, request_info = await AsyncRequest.get(url, delay=Config.REQUEST_DELAY, session=session)
            html_parse = BeautifulSoup(content, "html.parser")
            metadata = {
                "title": html_parse.find("h2", class_="title-film-detail-2").text.strip(),
                "title_vietnamese": html_parse.find("h1", class_="title-film-detail-1").text.strip()
            }
            metadata["watch_url"] = html_parse.find("a", class_="play-film")["href"]
            metadata["vietnamese_description"] = html_parse.find("p", class_="content-film").text.strip()
            for li in html_parse.find("ul", class_="infomation-film").findAll("li"):
                # Diễn viên: Emma Stone, Zac Efron
                info = li.text.split(":")
                field = info[0].strip() # Diễn viên
                if field in SWITCHER:
                    metadata[SWITCHER[field]] = info[1].strip() # clean leading white spaces
            metadata["movie_id"] = re.match(r".*-(\d*)$", url)[1].strip()
            metadata["origin"] = Config.IDENTIFIER
            return metadata
        except Exception as e:
            if debug:
                print(f"get_movie_info(). Error: \n {repr(e)}")
        return None


    @classmethod
    @inject_async_session
    async def get_watch_button_url(self, url: str, content=None, session = None, debug=False) -> Optional[str]:
        if not content:
            content, request_info = await AsyncRequest.get(url, delay=Config.REQUEST_DELAY, session=session)

        try:
            html_parse = BeautifulSoup(content, "html.parser")
            return html_parse.find("a", class_="play-film")["href"]
        except Exception as e:
            if debug:
                print(f"get_watch_button_url(). Error: \n {repr(e)}")

        return None

if __name__ == "__main__":
    eloop = asyncio.new_event_loop()
    metadata = eloop.run_until_complete(MovieParser.get_movie_info("http://khoaitv.org/xemphim/shameless-season-10-mat-day-phan-10-13270", debug=True))
    print(metadata)
    episodes_urls = eloop.run_until_complete(MovieParser.get_episodes_urls(metadata["watch_url"], debug=True))
    print(episodes_urls)



        