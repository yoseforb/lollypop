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
from cgi import escape

from lollypop.define import Lp, ArtSize
from lollypop.track import Track
from lollypop.utils import translate_artist_name

######################################################################
######################################################################


# Widget to manage queue
class QueueWidget(Gtk.Popover):
    """
        Init Popover ui with a text entry and a scrolled treeview
    """
    def __init__(self):
        Gtk.Popover.__init__(self)

        self._timeout = None
        self._in_drag = False
        self._signal_id1 = None
        self._signal_id2 = None

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/QueueWidget.ui')

        self._model = Gtk.ListStore(GdkPixbuf.Pixbuf,  # Cover
                                    str,               # Artist
                                    str,               # icon
                                    int)               # id

        self._view = builder.get_object('view')
        self._view.set_model(self._model)
        self._view.set_property('fixed_height_mode', True)

        builder.connect_signals(self)

        self._widget = builder.get_object('widget')

        renderer0 = Gtk.CellRendererPixbuf()
        renderer0.set_property('stock-size', ArtSize.MEDIUM)
        column0 = Gtk.TreeViewColumn("pixbuf1", renderer0, pixbuf=0)
        column0.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        renderer1 = Gtk.CellRendererText()
        renderer1.set_property('ellipsize-set', True)
        renderer1.set_property('ellipsize', Pango.EllipsizeMode.END)
        column1 = Gtk.TreeViewColumn("text", renderer1, markup=1)
        column1.set_expand(True)
        column1.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        renderer2 = Gtk.CellRendererPixbuf()
        column2 = Gtk.TreeViewColumn('delete', renderer2)
        column2.add_attribute(renderer2, 'icon-name', 2)
        column2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        self._view.append_column(column0)
        self._view.append_column(column1)
        self._view.append_column(column2)

        self.add(self._widget)

    """
        Show queue popover
        Populate treeview with current queue
    """
    # TODO Threaded loading
    def do_show(self):
        size_setting = Lp.settings.get_value('window-size')
        if isinstance(size_setting[1], int):
            self.set_size_request(400, size_setting[1]*0.7)
        else:
            self.set_size_request(400, 600)

        for track_id in Lp.player.get_queue():
            album_id = Lp.tracks.get_album_id(track_id)
            artist_id = Lp.albums.get_artist_id(album_id)
            artist_name = Lp.artists.get_name(artist_id)
            track_name = Lp.tracks.get_name(track_id)
            pixbuf = Lp.art.get_album(album_id, ArtSize.MEDIUM)
            title = "<b>%s</b>\n%s" %\
                (escape(translate_artist_name(artist_name)),
                 escape(track_name))
            self._model.append([pixbuf,
                                title,
                                'user-trash-symbolic',
                                track_id])
            del pixbuf

        self._signal_id1 = Lp.player.connect('current-changed',
                                             self._on_current_changed)
        self._signal_id2 = self._model.connect('row-deleted',
                                               self._updated_rows)
        Gtk.Popover.do_show(self)

    """
        Clear model
    """
    def do_hide(self):
        if self._signal_id1:
            Lp.player.disconnect(self._signal_id1)
            self._signal_id1 = None
        if self._signal_id2:
            self._model.disconnect(self._signal_id2)
            self._signal_id2 = None
        Gtk.Popover.do_hide(self)
        self._model.clear()

#######################
# PRIVATE             #
#######################
    """
        Delete item if Delete was pressed
        @param widget unused, Gdk.Event
    """
    def _on_keyboard_event(self, widget, event):
        if Lp.player.get_queue():
            if event.keyval == 65535:
                path, column = self._view.get_cursor()
                iterator = self._model.get_iter(path)
                self._model.remove(iterator)

    """
        Pop first item in queue if it's current track id
        @param player object
    """
    def _on_current_changed(self, player):
        if len(self._model) > 0:
            row = self._model[0]
            if row[3] == player.current_track.id:
                iter = self._model.get_iter(row.path)
                self._model.remove(iter)

    """
        Mark as in drag
        @param unused
    """
    def _on_drag_begin(self, widget, context):
        self._in_drag = True

    """
        Mark as not in drag
        @param unused
    """
    def _on_drag_end(self, widget, context):
        self._in_drag = False

    """
        Update queue when a row has been deleted
        @param path as Gtk.TreePath
        @param data as unused
    """
    def _updated_rows(self, path, data):
        if self.is_visible():
            new_queue = []
            for row in self._model:
                if row[3]:
                    new_queue.append(row[3])
            Lp.player.set_queue(new_queue)

    """
        Delete row
        @param GtkTreeIter
    """
    def _delete_row(self, iterator):
        self._model.remove(iterator)

    """
        Play clicked item
        @param TreeView, TreePath, TreeViewColumn
    """
    def _on_row_activated(self, view, path, column):
        if self._timeout:
            return
        iterator = self._model.get_iter(path)
        if iterator:
            if column.get_title() == "delete":
                self._delete_row(iterator)
            else:
                # We don't want to play if we are
                # starting a drag & drop, so delay
                self._timeout = GLib.timeout_add(500,
                                                 self._play_track,
                                                 iterator)

    """
        Clear queue
        @param widget as Gtk.Button
    """
    def _on_button_clicked(self, widget):
        self._model.clear()

    """
        Play track for selected iter
        @param GtkTreeIter
    """
    def _play_track(self, iterator):
        self._timeout = None
        if not self._in_drag:
            value_id = self._model.get_value(iterator, 3)
            self._model.remove(iterator)
            Lp.player.load(Track(value_id))
