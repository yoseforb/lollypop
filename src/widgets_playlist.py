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

from gi.repository import Gtk, GLib, GdkPixbuf, Pango

from _thread import start_new_thread
from cgi import escape
from gettext import gettext as _

from lollypop.define import Lp, ArtSize, Type
from lollypop.widgets_track import TracksWidget
from lollypop.track import Track
from lollypop.utils import translate_artist_name


# Playlist Widget is similar to album detailed
# widget but show a cover grid as playlist cove
class PlaylistWidget(Gtk.Bin):
    """
        Init playlist Widget
        @param playlist name as str
    """
    def __init__(self, playlist_name):
        Gtk.Bin.__init__(self)
        self._playlist_name = playlist_name
        self._tracks = []
        self._stop = False

        self._main_widget = Gtk.Grid()
        self._main_widget.set_property('margin', 10)
        self._main_widget.set_property('column-spacing', 10)
        self._main_widget.show()

        self._tracks_widget1 = TracksWidget(False)
        self._tracks_widget2 = TracksWidget(False)
        self._tracks_widget1.connect('activated',
                                     self._on_activated, playlist_name)
        self._tracks_widget2.connect('activated',
                                     self._on_activated, playlist_name)
        self._tracks_widget1.show()
        self._tracks_widget2.show()

        size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        size_group.add_widget(self._tracks_widget1)
        size_group.add_widget(self._tracks_widget2)

        self._main_widget.add(self._tracks_widget1)
        self._main_widget.add(self._tracks_widget2)

        self.add(self._main_widget)

    """
        Populate list one, thread safe
        @param track's ids as array of int
        @param track position as int
    """
    def populate_list_one(self, tracks, pos):
        self._stop = False
        self._tracks = list(tracks)
        GLib.idle_add(self._add_tracks,
                      tracks,
                      self._tracks_widget1,
                      pos)

    """
        Populate list two, thread safe
        @param track's ids as array of int
        @param track position as int
    """
    def populate_list_two(self, tracks, pos):
        self._stop = False
        self._tracks += list(tracks)
        GLib.idle_add(self._add_tracks,
                      tracks,
                      self._tracks_widget2,
                      pos)

    """
        Update playing indicator
    """
    def update_playing_indicator(self):
        self._tracks_widget1.update_playing(Lp.player.current_track.id)
        self._tracks_widget2.update_playing(Lp.player.current_track.id)

    """
        Stop loading
    """
    def stop(self):
        self._stop = True

    """
        Clear tracks
    """
    def clear(self):
        self._tracks = []
        for child in self._tracks_widget1.get_children():
            child.destroy()
        for child in self._tracks_widget2.get_children():
            child.destroy()

#######################
# PRIVATE             #
#######################
    """
        Add tracks to list
        @param tracks id as array of [int]
        @param widget TracksWidget
        @param track position as int
        @param previous album id as int
    """
    def _add_tracks(self, tracks, widget, pos, previous_album_id=None):
        if not tracks or self._stop:
            return

        track_id = tracks.pop(0)
        if track_id == -1:
            return

        (title, filepath, length, album_id) =\
            Lp.tracks.get_infos(track_id)
        if title is None:
            return
        else:
            title = escape(title)

        artist_id = Lp.albums.get_artist_id(album_id)
        artist_ids = Lp.tracks.get_artist_ids(track_id)
        # If we are listening to a compilation, prepend artist name
        if artist_id == Type.COMPILATIONS or\
           len(artist_ids) > 1 or\
           artist_id not in artist_ids:
            artist_name = ""
            for artist_id in artist_ids:
                artist_name += translate_artist_name(
                    Lp.artists.get_name(artist_id)) + ", "
            title = "<b>%s</b>\n%s" % (escape(artist_name[:-2]),
                                       title)

        if album_id != previous_album_id:
            widget.add_album(track_id, album_id, pos, title, length, None)
        else:
            widget.add_track(track_id, pos, title, length, None)
        GLib.idle_add(self._add_tracks, tracks, widget, pos+1, album_id)

    """
        On track activation, play track
        @param widget as TracksWidget
        @param track id as int
        @param playlist name as str
    """
    def _on_activated(self, widget, track_id, playlist_name):
        if not Lp.player.is_party():
            track = Lp.player.set_user_playlist(self._tracks, track_id)
            if track is not None:
                Lp.player.load(track)
        else:
            Lp.player.load(Track(track_id))


# Dialog for manage playlists (add, rename, delete, add object to)
class PlaylistsManagerWidget(Gtk.Bin):

    """
        Init ui with a scrolled treeview
        @param object id as int
        @param genre id as int
        @param is album as bool
    """
    def __init__(self, object_id, genre_id, is_album):
        Gtk.Bin.__init__(self)
        self._genre_id = genre_id
        self._object_id = object_id
        self._is_album = is_album
        self._deleted_path = None
        self._del_pixbuf = Gtk.IconTheme.get_default().load_icon(
            "list-remove-symbolic",
            22,
            0)

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/'
                                  'PlaylistsManagerWidget.ui')
        self._infobar = builder.get_object('infobar')
        self._infobar_label = builder.get_object('infobarlabel')

        self._model = Gtk.ListStore(bool, str, str)
        self._model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self._model.set_sort_func(1, self._sort_items)

        self._view = builder.get_object('view')
        self._view.set_model(self._model)

        builder.connect_signals(self)

        self.add(builder.get_object('widget'))

        if self._object_id != -1:
            renderer0 = Gtk.CellRendererToggle()
            renderer0.set_property('activatable', True)
            renderer0.connect('toggled', self._on_playlist_toggled)
            column0 = Gtk.TreeViewColumn("toggle", renderer0, active=0)

        renderer1 = Gtk.CellRendererText()
        renderer1.set_property('ellipsize-set', True)
        renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer1.set_property('editable', True)
        renderer1.connect('edited', self._on_playlist_edited)
        renderer1.connect('editing-started', self._on_playlist_editing_start)
        renderer1.connect('editing-canceled', self._on_playlist_editing_cancel)
        column1 = Gtk.TreeViewColumn('text', renderer1, text=1)
        column1.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column1.set_expand(True)

        renderer2 = Gtk.CellRendererPixbuf()
        column2 = Gtk.TreeViewColumn('delete', renderer2)
        column2.add_attribute(renderer2, 'icon-name', 2)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        if self._object_id != -1:
            self._view.append_column(column0)
        self._view.append_column(column1)
        self._view.append_column(column2)

    """
        Populate playlists, thread safe
    """
    def populate(self):
        # Search if we need to select item or not
        playlists = Lp.playlists.get()
        GLib.idle_add(self._append_playlists, playlists)

    """
        Add new playlist
    """
    def add_new_playlist(self):
        existing_playlists = []
        for item in self._model:
            existing_playlists.append(item[1])

        # Search for an available name
        count = 1
        name = _("New playlist ")+str(count)
        while name in existing_playlists:
            count += 1
            name = _("New playlist ")+str(count)
        self._model.append([True, name, 'user-trash-symbolic'])
        Lp.playlists.add(name)
        self._set_current_object(name, True)
#######################
# PRIVATE             #
#######################
    """
        Sort model
    """
    def _sort_items(self, model, itera, iterb, data):
        a = model.get_value(itera, 1)
        b = model.get_value(iterb, 1)
        return a.lower() > b.lower()

    """
        Append a playlist
        @param playlists as [str]
        @param playlist selected as bool
    """
    def _append_playlists(self, playlists):
        if playlists:
            playlist = playlists.pop(0)
            if self._object_id != -1:
                selected = Lp.playlists.is_present(playlist[1],
                                                   self._object_id,
                                                   self._genre_id,
                                                   self._is_album)
            else:
                selected = False
            self._model.append([selected, playlist[1], 'user-trash-symbolic'])
            GLib.idle_add(self._append_playlists, playlists)
        else:
            self._view.get_selection().unselect_all()

    """
        Show infobar
        @param path as Gtk.TreePath
    """
    def _show_infobar(self, path):
        iterator = self._model.get_iter(path)
        self._deleted_path = path
        self._infobar_label.set_text(_("Remove \"%s\"?") %
                                     self._model.get_value(iterator, 1))
        self._infobar.show()

    """
        Hide infobar
        @param widget as Gtk.Infobar
        @param reponse id as int
    """
    def _on_response(self, infobar, response_id):
        if response_id == Gtk.ResponseType.CLOSE:
            self._infobar.hide()
            self._view.grab_focus()
            self._view.get_selection().unselect_all()

    """
        Delete playlist
        @param TreeView, TreePath, TreeViewColumn
    """
    def _on_row_activated(self, view, path, column):
        iterator = self._model.get_iter(path)
        if iterator:
            if column.get_title() == "delete":
                self._show_infobar(path)

    """
        Delete playlist after confirmation
        @param button as Gtk.Button
    """
    def _on_delete_confirm(self, button):
        if self._deleted_path:
            iterator = self._model.get_iter(self._deleted_path)
            Lp.playlists.delete(self._model.get_value(iterator, 1))
            self._model.remove(iterator)
            self._deleted_path = None
            self._infobar.hide()
            self._view.grab_focus()
            self._view.get_selection().unselect_all()

    """
        Delete item if Delete was pressed
        @param widget unused, Gdk.Event
    """
    def _on_keyboard_event(self, widget, event):
        if event.keyval == 65535:
            path, column = self._view.get_cursor()
            self._show_infobar(path)

    """
        When playlist is activated, add object to playlist
        @param widget as cell renderer
        @param path as str representation of Gtk.TreePath
    """
    def _on_playlist_toggled(self, view, path):
        iterator = self._model.get_iter(path)
        toggle = not self._model.get_value(iterator, 0)
        name = self._model.get_value(iterator, 1)
        self._model.set_value(iterator, 0, toggle)
        self._set_current_object(name, toggle)

    """
        Add/Remove current object to playlist
        @param playlist name as str
        @param add as bool
    """
    def _set_current_object(self, name, add):
        # No current object
        if self._object_id == -1:
            return
        # Add or remove object from playlist
        if self._is_album:
            tracks_path = Lp.albums.get_tracks_path(self._object_id,
                                                    self._genre_id)
        else:
            tracks_path = [Lp.tracks.get_path(self._object_id)]

        if add:
            Lp.playlists.add_tracks(name, tracks_path)
        else:
            Lp.playlists.remove_tracks(name, tracks_path)

    """
        When playlist is edited, rename playlist
        @param widget as cell renderer
        @param path as str representation of Gtk.TreePath
        @param name as str
    """
    def _on_playlist_edited(self, widget, path, name):
        if name.find("/") != -1:
            return
        iterator = self._model.get_iter(path)
        old_name = self._model.get_value(iterator, 1)
        self._model.remove(iterator)
        self._model.append([True, name, 'user-trash-symbolic'])
        Lp.playlists.rename(name, old_name)

    """
        Disable global shortcuts
        @param widget as cell renderer
        @param editable as Gtk.CellEditable
        @param path as str representation of Gtk.TreePath
    """
    def _on_playlist_editing_start(self, widget, editable, path):
        Lp.window.enable_global_shorcuts(False)

    """
        Enable global shortcuts
        @param widget as cell renderer
    """
    def _on_playlist_editing_cancel(self, widget):
        Lp.window.enable_global_shorcuts(True)


# Dialog for edit a playlist
class PlaylistEditWidget(Gtk.Bin):

    """
        Init Popover ui with a text entry and a scrolled treeview
        @param playlist name as str
    """
    def __init__(self, playlist_name):
        Gtk.Bin.__init__(self)
        self._playlist_name = playlist_name
        self._save_on_disk = True
        self._tracks_orig = []

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/PlaylistEditWidget.ui')
        builder.connect_signals(self)

        self._infobar = builder.get_object('infobar')
        self._infobar_label = builder.get_object('infobarlabel')

        self._view = builder.get_object('view')

        self._model = Gtk.ListStore(GdkPixbuf.Pixbuf,
                                    str,
                                    str,
                                    str)
        self._model.connect("row-deleted", self._on_row_deleted)

        self._view.set_model(self._model)

        renderer0 = Gtk.CellRendererPixbuf()
        renderer0.set_property('stock-size', ArtSize.MEDIUM)
        column0 = Gtk.TreeViewColumn("pixbuf1", renderer0, pixbuf=0)

        renderer1 = Gtk.CellRendererText()
        renderer1.set_property('ellipsize-set', True)
        renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
        column1 = Gtk.TreeViewColumn("text1", renderer1, markup=1)
        column1.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column1.set_expand(True)

        renderer2 = Gtk.CellRendererPixbuf()
        column2 = Gtk.TreeViewColumn('delete', renderer2)
        column2.add_attribute(renderer2, 'icon-name', 2)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        self._view.append_column(column0)
        self._view.append_column(column1)
        self._view.append_column(column2)
        self.add(builder.get_object('widget'))

    """
        populate view if needed
    """
    def populate(self):
        if len(self._model) == 0:
            start_new_thread(self._append_tracks, ())

#######################
# PRIVATE             #
#######################
    """
        Delete tracks after confirmation
        @param button as Gtk.Button
    """
    def _on_delete_confirm(self, button):
        self._save_on_disk = False
        selection = self._view.get_selection()
        selected = selection.get_selected_rows()
        rows = []
        for item in selected[1]:
            rows.append(Gtk.TreeRowReference.new(self._model, item))

        for row in rows:
            iterator = self._model.get_iter(row.get_path())
            self._model.remove(iterator)
        self._infobar.hide()
        self._save_on_disk = True
        self._unselectall()
        self._update_on_disk()

    """
        Unselect all in view
    """
    def _unselectall(self):
        self._view.get_selection().unselect_all()
        self._view.grab_focus()

    """
        Append tracks, thread safe
    """
    def _append_tracks(self):
        sql = Lp.db.get_cursor()
        tracks = Lp.playlists.get_tracks_id(self._playlist_name, sql)
        GLib.idle_add(self._append_track, tracks)

    """
        Append track while tracks not empty
        @param tracks as [track_id as int]
    """
    def _append_track(self, tracks):
        if tracks:
            track_id = tracks.pop(0)
            filepath = Lp.tracks.get_path(track_id)
            album_id = Lp.tracks.get_album_id(track_id)
            artist_id = Lp.tracks.get_aartist_id(track_id)
            if artist_id == Type.COMPILATIONS:
                artist_ids = Lp.tracks.get_artist_ids(track_id)
                artist_name = ""
                for artist_id in artist_ids:
                    artist_name += translate_artist_name(Lp.artists.
                                                         get_name(artist_id))\
                        + ", "
                artist_name = artist_name[:-2]
            else:
                artist_name = Lp.artists.get_name(artist_id)
            track_name = Lp.tracks.get_name(track_id)
            art = Lp.art.get_album(album_id, ArtSize.SMALL)
            self._model.append([art,
                               "<b>%s</b>\n%s" % (
                                   escape(translate_artist_name(artist_name)),
                                   escape(track_name)),
                                'user-trash-symbolic', filepath])
            self._tracks_orig.append(filepath)
            GLib.idle_add(self._append_track, tracks)
        else:
            self._view.grab_focus()
            self._in_thread = False

    """
        Delete item if Delete was pressed
        @param widget unused, Gdk.Event
    """
    def _on_keyboard_event(self, widget, event):
        if event.keyval == 65535:
            path, column = self._view.get_cursor()
            self._show_infobar(path)

    """
        Show infobar
        @param path as Gtk.TreePath
    """
    def _show_infobar(self, path):
        iterator = self._model.get_iter(path)
        self._infobar_label.set_markup(_("Remove \"%s\"?") %
                                       self._model.get_value(iterator,
                                                             1).replace('\n',
                                                                        ' - '))
        self._infobar.show()

    """
        Hide infobar
        @param widget as Gtk.Infobar
        @param reponse id as int
    """
    def _on_response(self, infobar, response_id):
        if response_id == Gtk.ResponseType.CLOSE:
            self._infobar.hide()
            self._view.grab_focus()
            self._view.get_selection().unselect_all()

    """
        Delete playlist
        @param TreeView, TreePath, TreeViewColumn
    """
    def _on_row_activated(self, view, path, column):
        iterator = self._model.get_iter(path)
        if iterator:
            if column.get_title() == "delete":
                self._show_infobar(path)
            else:
                self._infobar.hide()

    """
        On selection changed, show infobar
        @param selection as Gtk.TreeSelection
    """
    def _on_selection_changed(self, selection):
        count = selection.count_selected_rows()
        if count > 1:
            self._infobar_label.set_markup(_("Remove these tracks?"))
            self._infobar.show()

    """
        Only catch drag & drop successful
        @param path as Gtk.TreePath
        @param data as unused
    """
    def _on_row_deleted(self, path, data):
        if self._save_on_disk:
            self._update_on_disk()

    """
        Update playlist on disk
    """
    def _update_on_disk(self):
        tracks_path = []
        for item in self._model:
            tracks_path.append(item[3])
        if tracks_path != self._tracks_orig:
            Lp.playlists.set_tracks(self._playlist_name, tracks_path)
