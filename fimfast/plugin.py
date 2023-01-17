from database.moviedb_async import AsyncMovieCollection, AsyncMovieInstanceCollection
from fimfast.parser.general import GeneralParser
from fimfast.parser.movie import MovieParser
from custom_request.request import AsyncSession
from utils.helper import chunk_iterator
from fimfast.config import Config
import asyncio
from pymongo import ReturnDocument
import argparse


class FimFast:

    @classmethod
    async def populate(cls, debug=False):
        aux = {}
        categories = await GeneralParser.get_categories_page(debug=debug)
        categorized_movies_urls, total_links =  await GeneralParser.get_categorized_movie_urls(categories, aux = aux, debug=debug)
        movies_urls = {url for movies_urls in categorized_movies_urls.values() for url in movies_urls}
        print("Total: "+str(len(movies_urls)))
        async def _update_db_wrapper(metadata):
             # check if we have already added this movie 
            try:
                instance = await AsyncMovieInstanceCollection.find_one_and_update({"origin": Config.IDENTIFIER, "movie_id": metadata["movie_id"]}, 
                                                                                  {"$set": metadata},
                                                                                  upsert=True, 
                                                                                  return_document=ReturnDocument.AFTER)

                # merge all instances of the same movie on different sites into one main instance
                # create the main movie instance if not exists
                matching_movie = await AsyncMovieInstanceCollection.mergeWithCorrespondingMovie(instance=instance)
                print(matching_movie)
            except Exception as e:
                if debug:
                    print("Error while _update_db_wrapper")
                    print(e)
                raise e
    
        async def _routine_wrapper(url, session):
            movieMetadata = []
            metadata = None
            try:
                metadata = await MovieParser.get_movie_info(url, pre_metadata=aux.get(url), debug=debug, session=session)
            except Exception as e:
                if debug:
                    print("Error while get_movie_info")
                    print(e)
                return

            print(metadata)
            await _update_db_wrapper(metadata)


        # process 20 urls at a time to avoid 500 http error
        for urls_range in chunk_iterator(movies_urls, 20):
            session = AsyncSession()
            await asyncio.gather(*(_routine_wrapper(url, session) for url in urls_range))
            await session.close()

    @classmethod
    async def mergeMovies(cls, debug=False):
        instances =  await AsyncMovieInstanceCollection.find({"origin" : Config.IDENTIFIER}).to_list(length=None)
        if debug:
            print(instances)
        # stop = False
        async def _routine(instance):
            # merge all instances of the same movie on different sites into one main instance
            # create the main movie instance if not exists
            if debug:
                print(f"Finding matching movie for instance: {str(instance)}")
            matching_movie = await AsyncMovieInstanceCollection.mergeWithCorrespondingMovie(instance=instance)
            print(matching_movie)

        await asyncio.gather(*(_routine(instance) for instance in instances))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--merge', default=False, action='store_true')
    parser.add_argument('--populate', action='store_true', default=True)
    args = parser.parse_args()
    eloop = asyncio.get_event_loop()
    if(args.merge):
        eloop.run_until_complete(FimFast.mergeMovies(debug=True))
    else:
        eloop.run_until_complete(FimFast.populate(debug=True))








        
        
