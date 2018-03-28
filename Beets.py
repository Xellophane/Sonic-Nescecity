import beets
from beets import config
from beets import importer
from beets.ui import _open_library


class Beets(object):
    """a minimal wrapper for using beets in a 3rd party application
       as a music library."""

    def __init__(self, music_library_file_name):
        """ music_library_file_name = full path and name of
            music database to use """
        "configure to keep music in place and do not auto-tag"
        config.set_file('config.yaml')
        config.resolve()
        config["library"] = music_library_file_name
        config["threaded"] = True

        # create/open the the beets library
        self.lib = _open_library(config)

    def query(self, query=None):
        """return list of items from the music DB that match the given query"""
        return self.lib.items(query)
