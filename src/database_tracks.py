#!/usr/bin/python
# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gettext import gettext as _

from lollypop.define import Lp, Type


# All functions take a sqlite cursor as last parameter,
# set another one if you're in a thread
class TracksDatabase:
    def __init__(self):
        pass

    """
        Add a new track to database
        @param name as string
        @param filepath as string,
        @param length as int
        @param tracknumber as int
        @param discnumber as int
        @param album_id as int
        @param genre_id as int
        @param year as int
        @param mtime as int
        @warning: commit needed
    """
    def add(self, name, filepath, length, tracknumber, discnumber,
            album_id, year, mtime, sql=None):
        if not sql:
            sql = Lp.sql
        # Invalid encoding in filenames may raise an exception
        try:
            sql.execute(
                "INSERT INTO tracks (name, filepath, length, tracknumber,\
                discnumber, album_id, year, mtime) VALUES\
                (?, ?, ?, ?, ?, ?, ?, ?)", (name,
                                            filepath,
                                            length,
                                            tracknumber,
                                            discnumber,
                                            album_id,
                                            year,
                                            mtime))
        except Exception as e:
            print("TracksDatabase::add: ", e, ascii(filepath))

    """
        Add artist to track
        @param track id as int
        @param artist id as int
        @warning: commit needed
    """
    def add_artist(self, track_id, artist_id, sql=None):
        if not sql:
            sql = Lp.sql
        artists = self.get_artist_ids(track_id, sql)
        if artist_id not in artists:
            sql.execute("INSERT INTO "
                        "track_artists (track_id, artist_id)"
                        "VALUES (?, ?)", (track_id, artist_id))

    """
        Add genre to track
        @param track id as int
        @param genre id as int
        @warning: commit needed
    """
    def add_genre(self, track_id, genre_id, sql=None):
        if not sql:
            sql = Lp.sql
        genres = self.get_genre_ids(track_id, sql)
        if genre_id not in genres:
            sql.execute("INSERT INTO "
                        "track_genres (track_id, genre_id)"
                        "VALUES (?, ?)", (track_id, genre_id))

    """
        Return track id for path
        @param filepath as str
    """
    def get_id_by_path(self, filepath, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT rowid FROM tracks where filepath=?",
                             (filepath,))
        v = result.fetchone()
        if v:
            return v[0]

        return None

    """
        Get track name for track id
        @param Track id as int
        @return Name as string
    """
    def get_name(self, track_id, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT name FROM tracks where rowid=?",
                             (track_id,))
        v = result.fetchone()
        if v:
            return v[0]

        return ""

    """
        Get track year
        @param track id as int
        @return track year as string
    """
    def get_year(self, album_id, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT year FROM tracks where rowid=?",
                             (album_id,))
        v = result.fetchone()
        if v:
            if v[0]:
                return str(v[0])

        return ""

    """
        Get track path for track id
        @param Track id as int
        @return Path as string
    """
    def get_path(self, track_id, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT filepath FROM tracks where rowid=?",
                             (track_id,))
        v = result.fetchone()
        if v:
            return v[0]

        return ""

    """
        Get album id for track id
        @param track id as int
        @return album id as int
    """
    def get_album_id(self, track_id, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT album_id FROM tracks where rowid=?",
                             (track_id,))
        v = result.fetchone()
        if v:
            return v[0]

        return -1

    """
        Get album name for track id
        @param track id as int
        @return album name as str
    """
    def get_album_name(self, track_id, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT albums.name from albums,tracks\
                              WHERE tracks.rowid=? AND\
                              tracks.album_id=albums.rowid", (track_id,))
        v = result.fetchone()
        if v:
            return v[0]

        return _("Unknown")

    """
        Get artist ids
        @param track id as int
        @return artist ids as [int]
    """
    def get_artist_ids(self, track_id, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT artist_id FROM track_artists\
                              WHERE track_id=?", (track_id,))
        artists = []
        for row in result:
            artists += row
        return artists

    """
        Get genre ids
        @param track id as int
        @return genre ids as [int]
    """
    def get_genre_ids(self, track_id, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT genre_id FROM track_genres\
                              WHERE track_id=?", (track_id,))
        genres = []
        for row in result:
            genres += row
        return genres

    """
        Get genre name
        @param track id as int
        @return Genre name as str "genre1 genre2_..."
    """
    def get_genre_name(self, track_id, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT name FROM genres, track_genres\
                              WHERE track_genres.track_id=?\
                              AND track_genres.genre_id=genres.rowid",
                             (track_id,))
        genres = ""
        for row in result:
            genres += row[0]
            genres += " "
        return genres

    """
        Get mtime for tracks
        WARNING: Should be called before anything is shown on screen
        @param None
        @return dict of {filepath as string: mtime as int}
    """
    def get_mtimes(self, sql=None):
        if not sql:
            sql = Lp.sql
        mtimes = {}
        sql.row_factory = self._dict_factory
        result = sql.execute("SELECT filepath, mtime FROM tracks")
        for row in result:
            mtimes.update(row)
        sql.row_factory = None
        return mtimes

    """
        Get all track informations for track id
        @param Track id as int
        @return (name as string, filepath as string,
        length as int, tracknumber as int, album_id as int)
        Returned values can be (None, None, None, None)
    """
    def get_infos(self, track_id, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT name, filepath,\
                              length, album_id\
                              FROM tracks WHERE rowid=?", (track_id,))
        v = result.fetchone()
        if v:
            return v
        return (None, None, None, None)

    """
        Get aartist id for track id
        @param Track id as int
        @return Performer id as int
    """
    def get_aartist_id(self, track_id, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT albums.artist_id from albums,tracks\
                              WHERE tracks.rowid=?\
                              AND tracks.album_id ==\
                              albums.rowid", (track_id,))
        v = result.fetchone()

        if v:
            return v[0]

        return Type.COMPILATIONS

    """
        Get all tracks filepath
        @param None
        @return Array of filepath as string
    """
    def get_paths(self, sql=None):
        if not sql:
            sql = Lp.sql
        tracks = []
        result = sql.execute("SELECT filepath FROM tracks;")
        for row in result:
            tracks += row
        return tracks

    """
        Get track position in album
        @param track id as int
        @return position as int
    """
    def get_number(self, track_id, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT tracknumber FROM tracks\
                              WHERE rowid=?", (track_id,))
        v = result.fetchone()
        if v:
            return v[0]

        return 0

    """
        Get track length for track id
        @param Track id as int
        @return length as int
    """
    def get_length(self, track_id, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT length FROM tracks\
                              WHERE rowid=?", (track_id,))
        v = result.fetchone()
        if v:
            return v[0]

        return 0

    """
        Return True if no tracks in db
    """
    def is_empty(self, sql=None):
        if not sql:
            sql = Lp.sql
        result = sql.execute("SELECT COUNT(*) FROM tracks  LIMIT 1")
        v = result.fetchone()
        if v:
            return v[0] == 0

        return True

    """
        Get tracks for artist_id where artist_id isn't main artist
        @param artist id as int
        @return array of (tracks id as int, track name as string)
    """
    def get_as_non_aartist(self, artist_id, sql=None):
        if not sql:
            sql = Lp.sql
        tracks = []
        result = sql.execute("SELECT tracks.rowid, tracks.name\
                              FROM tracks, track_artists, albums\
                              WHERE albums.rowid == tracks.album_id\
                              AND track_artists.artist_id=?\
                              AND track_artists.track_id=tracks.rowid\
                              AND albums.artist_id != ?", (artist_id,
                                                           artist_id))
        for row in result:
            tracks += (row,)
        return tracks

    """
        Clean database for track id
        @param track_id as int
        @warning commit needed
    """
    def clean(self, track_id, sql=None):
        if not sql:
            sql = Lp.sql
        sql.execute("DELETE FROM track_artists\
                     WHERE track_id = ?", (track_id,))
        sql.execute("DELETE FROM track_genres\
                     WHERE track_id = ?", (track_id,))

    """
        Search for tracks looking like string
        @param string
        return: Arrays of (id as int, name as string)
    """
    def search(self, string, sql=None):
        if not sql:
            sql = Lp.sql
        tracks = []
        result = sql.execute("SELECT rowid, name FROM tracks\
                              WHERE name LIKE ? LIMIT 25", ('%'+string+'%',))
        for row in result:
            tracks += (row,)
        return tracks

    """
        Remove track
        @param Track path as string
    """
    def remove(self, path, sql=None):
        if not sql:
            sql = Lp.sql
        track_id = self.get_id_by_path(path, sql)
        sql.execute("DELETE FROM track_genres\
                     WHERE track_id=?", (track_id,))
        sql.execute("DELETE FROM track_artists\
                     WHERE track_id=?", (track_id,))
        sql.execute("DELETE FROM tracks\
                     WHERE rowid=?", (track_id,))

#######################
# PRIVATE             #
#######################
    """
        Sqlite row factory
    """
    def _dict_factory(self, cursor, row):
        d = {}
        d[row[0]] = row[1]
        return d
