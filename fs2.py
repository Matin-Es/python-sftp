# SFTP File Transfer Application
# This is a Tkinter-based GUI application for uploading and downloading files via SFTP

# Import necessary libraries
import tkinter as tk  # For creating graphical user interface
from tkinter import filedialog, messagebox  # For file selection and message popups
import paramiko  # For SFTP file transfer protocol
import os  # For file and path operations
import time  # For time-related operations
from tkinter import ttk  # For themed Tkinter widgets
import threading  # For running file transfers in background
import json  # For saving and loading transfer history
from datetime import datetime  # For timestamp generation


class FileSharingApp:
    def __init__(self, root):
        """
        Initialize the File Sharing Application

        This method sets up the entire user interface, including:
        - Server connection inputs
        - File upload and download sections
        - Transfer history display
        - Themed UI components

        :param root: The main Tkinter window
        """
        # Load and apply custom theme for better UI appearance
        theme_path = os.path.join(os.path.dirname(__file__), "forest-light.tcl")
        root.tk.call("source", theme_path)
        ttk.Style().theme_use("forest-light")

        # Store the main window
        self.root = root
        # Set window title and size (in Arabic)
        self.root.title("SFTP انتقال فایل")
        self.root.geometry("400x800")  # Wide enough for all components
        self.root.resizable(False, False)  # Prevent window resizing

        # File to store transfer history
        self.history_file = "transfer_history.json"
        # Load existing transfer history
        self.transfer_history = self.load_history()

        # Create main container frame
        main_frame = ttk.Frame(root)
        main_frame.pack(expand=True, pady=10)

        # Create section labels, input fields, and buttons for server details
        ttk.Label(
            main_frame, text="مشخصات سرور", font=("Arial", 14, "bold"), anchor="e"
        ).pack(pady=10)

        # Create input frame for server details
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(pady=10)

        # Helper function to create labeled input fields
        def create_input(label, show=False):
            """
            Create a labeled input field

            :param label: Text label for the input
            :param show: Whether to mask the input (for passwords)
            :return: Entry widget
            """
            ttk.Label(input_frame, text=label, anchor="e").pack(anchor="e")
            entry = ttk.Entry(
                input_frame, show="*" if show else "", width=30, justify="right"
            )
            entry.pack(pady=5)
            return entry

        # Create input fields for server, username, and password
        self.server_entry = create_input("سرور")
        self.username_entry = create_input("نام کاربری")
        self.password_entry = create_input("کلمه عبور", show=True)

        # Create progress tracking components
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(pady=10, fill="x", padx=20)

        # Progress bar to show transfer progress
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, orient="horizontal", length=300, mode="determinate"
        )
        self.progress_bar.pack(fill="x")

        # Label to show progress details
        self.progress_label = ttk.Label(self.progress_frame, text="", anchor="center")
        self.progress_label.pack(pady=5)

        # Status label for upload operations
        self.upload_status_label = ttk.Label(
            main_frame, text="", foreground="blue", anchor="e"
        )
        self.upload_status_label.pack()

        # Button to select file for upload
        ttk.Button(
            main_frame, text="انتخاب فایل", command=self.select_file, width=20
        ).pack(pady=10)

        # Label to show selected file details
        self.file_label = ttk.Label(
            main_frame, text="فایلی انتخاب نشده", foreground="gray", anchor="e"
        )
        self.file_label.pack(pady=5)

        # Button to start file upload
        ttk.Button(
            main_frame, text="بارگذاری فایل", command=self.upload_file, width=20
        ).pack(pady=10)

        # Download section
        ttk.Label(
            main_frame, text="دانلود فایل", font=("Arial", 12, "bold"), anchor="e"
        ).pack(pady=10)

        # Download frame
        download_frame = ttk.Frame(main_frame)
        download_frame.pack(fill="x", padx=60)

        # Remote file name input for download
        ttk.Label(download_frame, text="نام فایل", anchor="e").pack(fill="x")
        self.remote_file_entry = ttk.Entry(download_frame, width=30, justify="right")
        self.remote_file_entry.pack(pady=5)

        # Download status label
        self.download_status_label = ttk.Label(
            main_frame, text="", foreground="blue", anchor="e"
        )
        self.download_status_label.pack()

        # Button to start file download
        ttk.Button(
            main_frame, text="دانلود فایل", command=self.download_file, width=20
        ).pack(pady=10)

        # Transfer history section
        ttk.Label(
            main_frame, text="تاریخچه انتقال", font=("Arial", 12, "bold"), anchor="e"
        ).pack(pady=10)

        # History frame
        history_frame = ttk.Frame(main_frame)
        history_frame.pack(fill="both", expand=True, padx=20)

        # Create Treeview to display transfer history
        self.history_tree = ttk.Treeview(
            history_frame,
            columns=("date", "type", "file", "status"),
            show="headings",
            height=5,
        )

        # Configure column headings
        self.history_tree.heading("date", text="تاریخ", anchor="e")
        self.history_tree.heading("type", text="نوع", anchor="e")
        self.history_tree.heading("file", text="فایل", anchor="e")
        self.history_tree.heading("status", text="وضعیت", anchor="e")

        # Set column widths
        self.history_tree.column("date", width=100)
        self.history_tree.column("type", width=70)
        self.history_tree.column("file", width=120)
        self.history_tree.column("status", width=70)

        # Add scrollbar to history view
        scrollbar = ttk.Scrollbar(
            history_frame, orient="vertical", command=self.history_tree.yview
        )
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind right-click event for context menu
        self.history_tree.bind("<Button-3>", self.show_context_menu)

        # Create context menu for history
        self.context_menu = tk.Menu(root, tearoff=0)
        self.context_menu.add_command(
            label="حذف این مورد", command=self.delete_selected_history
        )

        # History control buttons frame
        history_buttons_frame = ttk.Frame(main_frame)
        history_buttons_frame.pack(pady=5)

        # Buttons to clear or delete selected history entries
        ttk.Button(
            history_buttons_frame,
            text="پاک کردن تاریخچه",
            command=self.clear_history,
            width=20,
        ).pack(side="left", padx=5)

        ttk.Button(
            history_buttons_frame,
            text="حذف انتخاب شده",
            command=self.delete_selected_history,
            width=20,
        ).pack(side="left", padx=5)

        # Status label for general application status
        self.status_label = ttk.Label(
            main_frame, text="", foreground="blue", anchor="e"
        )
        self.status_label.pack(pady=10)

        # Load and display existing transfer history
        self.update_history_display()

    def select_file(self):
        """
        Open file dialog to select a file for upload
        Updates the file label with selected file details
        """
        # Open file selection dialog
        self.file_path = filedialog.askopenfilename()

        # Update file label with selected file info
        if self.file_path:
            file_size = os.path.getsize(self.file_path)
            self.file_label.config(
                text=f"انتخاب شده: {os.path.basename(self.file_path)} ({file_size} bytes)"
            )
        else:
            self.file_label.config(text="فایلی انتخاب نشده")

    def show_context_menu(self, event):
        """
        Display context menu when right-clicking on history entry

        :param event: Tkinter event object
        """
        # Identify the row clicked
        item = self.history_tree.identify_row(event.y)
        if item:
            # Select the item and show context menu
            self.history_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def delete_selected_history(self):
        """
        Delete selected entries from transfer history
        Asks for user confirmation before deletion
        """
        # Check if any item is selected
        selected_items = self.history_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "لطفا یک مورد را انتخاب کنید")
            return

        # Confirm deletion
        if messagebox.askyesno(
            "Delete", "آیا مطمئن هستید که می‌خواهید موارد انتخاب شده را حذف کنید؟"
        ):
            # Remove selected items from history
            for item_id in selected_items:
                item_values = self.history_tree.item(item_id)["values"]
                # Find and remove corresponding entry
                for i, entry in enumerate(self.transfer_history):
                    if (
                        entry["date"] == item_values[0]
                        and entry["file"] == item_values[2]
                        and entry["status"]
                        == ("success" if item_values[3] == "موفق" else "failed")
                    ):
                        del self.transfer_history[i]
                        break

            # Save and update history
            self.save_history()
            self.update_history_display()

    def update_progress(self, transferred, total):
        """
        Update progress bar during file transfer

        :param transferred: Number of bytes transferred
        :param total: Total number of bytes to transfer
        """
        # Calculate and display transfer progress
        percentage = (transferred / total) * 100
        self.progress_bar["value"] = percentage
        self.progress_label.config(
            text=f"{percentage:.1f}% ({transferred}/{total} bytes)"
        )
        self.root.update_idletasks()

    def load_history(self):
        """
        Load transfer history from JSON file

        :return: List of transfer history entries
        """
        try:
            # Read history from file if it exists
            if os.path.exists(self.history_file):
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except:
            # Return empty list if file can't be read
            return []

    def save_history(self):
        """
        Save transfer history to JSON file
        """
        # Write transfer history to file
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.transfer_history, f, ensure_ascii=False, indent=2)

    def add_to_history(self, transfer_type, filename, status):
        """
        Add a new transfer entry to history

        :param transfer_type: 'upload' or 'download'
        :param filename: Name of transferred file
        :param status: 'success' or 'failed'
        """
        # Create new history entry with current timestamp
        self.transfer_history.append(
            {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "type": transfer_type,
                "file": filename,
                "status": status,
            }
        )
        # Save and update history display
        self.save_history()
        self.update_history_display()

    def update_history_display(self):
        """
        Refresh the history treeview with current transfer history
        """
        # Clear existing items in treeview
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        # Add history items in reverse chronological order
        for item in reversed(self.transfer_history):
            self.history_tree.insert(
                "",
                "end",
                values=(
                    item["date"],
                    "آپلود" if item["type"] == "upload" else "دانلود",
                    item["file"],
                    "موفق" if item["status"] == "success" else "ناموفق",
                ),
            )

    def clear_history(self):
        """
        Completely clear transfer history after user confirmation
        """
        # Ask for confirmation before clearing
        if messagebox.askyesno(
            "Clear History", "آیا مطمئن هستید که می‌خواهید تاریخچه را پاک کنید؟"
        ):
            # Reset history and update display
            self.transfer_history = []
            self.save_history()
            self.update_history_display()

    def upload_file(self):
        """
        Initiate file upload process in a separate thread
        """
        # Check if a file is selected
        if not hasattr(self, "file_path") or not self.file_path:
            messagebox.showerror(
                "Error", "لطفا فایل مورد نظر برای آپلود را انتخاب کنید!"
            )
            return

        # Start upload in a background thread to prevent UI freezing
        threading.Thread(
            target=self._transfer_file, args=("upload",), daemon=True
        ).start()

    def download_file(self):
        """
        Initiate file download process in a separate thread
        """
        # Get remote filename from input
        remote_file = self.remote_file_entry.get()
        if not remote_file:
            messagebox.showerror(
                "Error", "لطفا نام فایل ریموت برای دانلود را وارد کنید!"
            )
            return

        # Start download in a background thread
        threading.Thread(
            target=self._transfer_file,
            args=("download",),
            kwargs={"remote_file": remote_file},
            daemon=True,
        ).start()

    def _transfer_file(self, action, remote_file=None):
        """
        Manage file transfers via SFTP protocol with progress tracking

        This method handles both file uploads and downloads:
        1. Validates server connection details
        2. Establishes an SFTP connection
        3. Performs file transfer with progress updates
        4. Manages transfer history and user notifications

        :param action: Type of transfer - either 'upload' or 'download'
        :param remote_file: Name of file to download (only used for download action)
        """
        # Retrieve server connection details from input fields
        server, username, password = (
            self.server_entry.get(),
            self.username_entry.get(),
            self.password_entry.get(),
        )

        # Validate that all connection details are provided
        if not all([server, username, password]):
            # Show error if any connection detail is missing
            messagebox.showerror("Error", "لطفا تمامی مشخصات را پر کنید")
            return

        try:
            # Reset progress bar and label before starting transfer
            self.progress_bar["value"] = 0
            self.progress_label.config(text="")

            # Update status to show connection in progress
            self.status_label.config(text="درحال اتصال...", foreground="blue")

            # Create SFTP transport and connection
            # Uses standard SSH port 22
            transport = paramiko.Transport((server, 22))
            transport.connect(username=username, password=password)

            # Create SFTP client from the transport
            sftp = paramiko.SFTPClient.from_transport(transport)

            # Handle file upload
            if action == "upload":
                # Use the filename as the remote path (upload to root directory)
                remote_path = os.path.basename(self.file_path)

                # Get total file size for progress tracking
                file_size = os.path.getsize(self.file_path)

                # Create a callback function to update progress bar
                def callback(transferred, total):
                    # Use root.after to safely update UI from thread
                    self.root.after(0, self.update_progress, transferred, total)

                # Perform the file upload
                sftp.put(self.file_path, remote_path, callback=callback)

                # Update UI and history after successful upload
                self.root.after(
                    0,
                    self.status_label.config,
                    {"text": f"فایل آپلود شده در {remote_path}", "foreground": "green"},
                )
                self.add_to_history(
                    "upload", os.path.basename(self.file_path), "success"
                )

                # Show success message to user
                messagebox.showinfo(
                    "Success",
                    f"File '{os.path.basename(self.file_path)}' با موفقیت بارگذاری شد!",
                )

            # Handle file download
            elif action == "download":
                # Open save file dialog to choose download location
                save_path = filedialog.asksaveasfilename(initialfile=remote_file)

                # Cancel download if no save path selected
                if not save_path:
                    self.root.after(
                        0,
                        self.status_label.config,
                        {"text": "دانلود متوقف شد", "foreground": "red"},
                    )
                    self.add_to_history("download", remote_file, "failed")
                    return

                # Get total file size for progress tracking
                file_size = sftp.stat(remote_file).st_size

                # Create a callback function to update progress bar
                def callback(transferred, total):
                    # Use root.after to safely update UI from thread
                    self.root.after(0, self.update_progress, transferred, total)

                # Perform the file download
                sftp.get(remote_file, save_path, callback=callback)

                # Update UI and history after successful download
                self.root.after(
                    0,
                    self.status_label.config,
                    {"text": f"فایل ذخیره شد در {save_path}", "foreground": "green"},
                )
                self.add_to_history("download", remote_file, "success")

                # Show success message to user
                messagebox.showinfo(
                    "Success", f"File '{remote_file}' با موفقیت دانلود شد!"
                )

            # Close SFTP and transport connections
            sftp.close()
            transport.close()

        except Exception as e:
            # Handle any errors during transfer process
            # Show error message to user
            messagebox.showerror("Error", f"{action.capitalize()} ناموفق: {e}")

            # Reset status label
            self.root.after(
                0, self.status_label.config, {"text": "", "foreground": "red"}
            )

            # Add failed transfer to history
            self.add_to_history(
                action,
                (
                    remote_file
                    if action == "download"
                    else os.path.basename(self.file_path)
                ),
                "failed",
            )


# Main application startup
if __name__ == "__main__":
    # Create main Tkinter window
    root = tk.Tk()

    # Initialize and run the application
    app = FileSharingApp(root)
    root.mainloop()
