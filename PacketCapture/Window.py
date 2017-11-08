import fcntl
import os
import subprocess
import sys
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GObject


class PacketCaptureGTK:
    """A GUI for controlling the Packet.py script"""

    # Loads and shows the window
    def __init__(self):
        # Creates the builder and loads the UI from the glade file
        builder = Gtk.Builder()
        builder.add_from_file("PacketCaptureWindow.glade")
        builder.connect_signals(self)

        win = builder.get_object("window1")
        win.show_all()

        # Grabs and saves objects
        self.textBox_Latency = builder.get_object("TextBox_Latency")
        self.textBox_PacketLoss = builder.get_object("TextBox_PacketLoss")
        self.textView_ConsoleOutput = builder.get_object("TextView_ConsoleOutput")

        Gtk.main()
    # --------------------------Control Events------------------------------------- #

    def onStop_Clicked(self, button):
        try:
            self.sub_proc.kill()
            print('SIGINT Send')
        except:
            print("Error: Cannot stop process")

    def onDeleteWindow(self, *args):
        """Event that runs when the window is closed"""
        Gtk.main_quit(*args)

    def latency_Clicked(self, button):
        """Event that runs when the latency button is clicked"""

        error_message = \
            "Latency value entered is incorrect, it needs to be in the range of 1-1000ms"
        value = self.textBox_Latency.get_text()

        # Checks if the value is a valid int a checks for it's range
        if self.validation(value, 1, 1000):
            self.run_packet_capture("-l " + str(value))
        else:
            print(error_message)

    def packet_loss_Clicked(self, button):
        """Event that runs when the packet loss button is clicked"""

        error_message = \
            "Packet loss value entered is incorrect, it needs to be in the range of 1-100!"
        value = self.textBox_PacketLoss.get_text()

        # Checks if it is a valid int and if its within a specified range
        if self.validation(value, 1, 100):
            self.run_packet_capture("-pl " + str(value))
        else:
            print(error_message)
    # ----------------------------------------------------------------------------- #

    def run_packet_capture(self, parameters):
        """This method is used to run the Packet.py script"""

        # The exact location of the file needs to specified
        file_name = "Packet.py"
        file_path = "/home/user_1/PycharmProjects/Dissertation_Project/PacketCapture/" + file_name

        # Command parameters
        cmd = ['pkexec', 'python', file_path, parameters]

        # TODO: This is not working
        # -It will display commands that are not run under root perfectly
        # -But if a command requires elevation it will not work and will only display error messages?
        # -Maybe it's to do with different streams for root and regular users
        #self.sub_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # Runs the command - will display on a console for the time being
        self.sub_proc = subprocess.call(cmd)
        self.sub_outp = ""

        #GObject.timeout_add(100, self.update_terminal)

    def validation(self, string, start, stop):
        """This function is used to validate the passed parameter values
            it checks if the value can be parsed as an int and a range is
            specified that is must be within"""

        try:
            # Parsing
            integer = int(string)

            # Checks for the validation range
            if start <= integer <= stop:
                return True
            else:
                return False
        except ValueError:
            return False

    def update_terminal(self):
        """Used to pipe terminal output to a TextView"""

        # Grabs the buffer and finds the end
        buffer = self.textView_ConsoleOutput.get_buffer()

        end = buffer.get_end_iter()
        mark = buffer.create_mark('', end, False)

        # Grabs the console output
        bytes = self.non_block_read(self.sub_proc.stdout)

        if bytes is not None:
            # Display the output of the console
            buffer.insert(end, bytes.decode())

            # Keeps the most recent line on screen
            self.textView_ConsoleOutput.scroll_mark_onscreen(mark)

        return self.sub_proc.poll() is None

    def non_block_read(self, output):
        """Code for this was taken from @torfbolt answer on:
        https://stackoverflow.com/questions/17038063/show-terminal-output-in-a-gui-window-using-python-gtk
        """
        fd = output.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            return output.read()
        except:
            return ''


