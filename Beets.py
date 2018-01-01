import beets
from beets import config
from beets import importer
from beets.ui import _open_library


class Beets(object):
    """a minimal wrapper for using beets in a 3rd party application
       as a music library."""

    class AutoImportSession(importer.ImportSession):
        "a minimal session class for importing that does not change files"

        def should_resume(self, path):
            return True

        def choose_match(self, task):
            return importer.action.ASIS

        def resolve_duplicate(self, task, found_duplicates):
            pass

        def choose_item(self, task):
            return importer.action.ASIS

    def __init__(self, music_library_file_name):
        """ music_library_file_name = full path and name of
            music database to use """
        "configure to keep music in place and do not auto-tag"
        config["import"]["autotag"] = False
        config["import"]["copy"] = False
        config["import"]["move"] = False
        config["import"]["write"] = False
        config["library"] = music_library_file_name
        config["threaded"] = True

        # create/open the the beets library
        self.lib = _open_library(config)

    def import_files(self, list_of_paths):
        """import/reimport music from the list of paths.
            Note: This may need some kind of mutex as I
                  do not know the ramifications of calling
                  it a second time if there are background
                  import threads still running.
        """
        query = None
        loghandler = None  # or log.handlers[0]
        self.session = Beets.AutoImportSession(self.lib, loghandler,
                                               list_of_paths, query)
        self.session.run()

    def query(self, query=None):
        """return list of items from the music DB that match the given query"""
        return self.lib.items(query)
