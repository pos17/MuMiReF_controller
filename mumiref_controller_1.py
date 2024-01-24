

#Using threading. First, we launch a single-threaded tkinter and from it we launch a thread to work with the OSC server.

import time
import threading
import tkinter as tk


# Create a window with a button and a label.
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.button = tk.Button(self, command=self.start_action, text="start")
        self.button.pack(padx=100, pady=50)
        self.lable = tk.Label(self, text="initial value")
        self.lable.pack(padx=100, pady=50)

# We start an additional thread for the PSC Server.
    def start_action(self):
        self.button.config(state=tk.DISABLED)
        thread = threading.Thread(target=self.init_main)
        thread.start()
        self.check_thread(thread)

# We make the button active only after the flow is completed.
    def check_thread(self, thread):
        if thread.is_alive():
            self.check = self.after(500, lambda: self.check_thread(thread))
        else:
            self.button.config(state=tk.NORMAL)

    def init_main(self):
        # start dispatcher,server
        self.loop()  # Enter main loop of program
        # Clean up serve endpoint

    def loop(self):
        """Example main loop that only runs for 10 iterations before finishing"""
        for i in range(2):
            print(f"Loop {i}")
            self.lable.config(text=f"Loop {i}")
            time.sleep(1)



if __name__ == "__main__":
    app = App()
    app.mainloop()
