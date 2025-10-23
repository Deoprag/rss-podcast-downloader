# 🎧 Podcast Downloader

A simple desktop application built with **Flet (Python)** to list, search, and download podcast episodes from an RSS feed.

The goal is to provide a clean, interface for consuming podcast feeds, allowing users to download episodes individually or in batches, with queue management, cancellation, and progress indicators.

--- 

## 🚀 Features

- **Feed Loading:** Loads episodes from any podcast RSS feed.
- **Authentication:** Supports feeds protected with basic authentication or URL token authentication `url.com/rss/{token}`.
- **Individual Download:** Download any episode with a single click.
- **Batch Download:** Download all filtered episodes using the **"Download all"** button.
- **Save & Load Configurations:** Store podcast details (name, URL, folder, credentials) in a local SQLite database for quick access.
- **Queue Management:** Batch downloads are queued (🕓) and processed sequentially.
- **Cancellation:** Cancel individual downloads or the entire batch at any time.
- **Progress Indicators:**
  - **Individual:** A `ProgressRing` appears during download.
  - **Total:** A `ProgressBar` shows overall batch progress.
- **Dynamic Search:** Filter episodes by title or description in real-time.
- **Smart Sorting:** Sort episodes by:
  - **Newest** (default)
  - **Oldest** (If episode numbers like `#123` or `123 -` are found, sorting is based on them; otherwise, the feed’s chronological order is used.)
  > **Note:** Sorting uses episode numbers found after a hash (e.g., "Title #123"), at the start (e.g., "123 - Title"),  or at the end (e.g., "Title - 123") of the title (in the given order). If no number is detected in these patterns, the original feed order is used.
- **File Checking:** Already-downloaded episodes are marked with 📁 and skipped.
- **Folder Selection:** GUI for selecting the target download folder.

## 🧠 Technologies Used

- **Python 3**
- **Flet** — GUI framework
- **requests** — HTTP requests (fetch feed and files)
- **threading** — Keeps the UI responsive during downloads
- **xml.etree.ElementTree** — Parses RSS XML data
- **sqlite3** — Local database for saving configurations.

## ⚙️ How to Run

### Prerequisites

- Python **3.8+**
- `pip` (Python package manager)

### Installation

1. Clone this repository into a folder.
2. Open a terminal or command prompt in the same folder.
3. *(Recommended)* Create and activate a virtual environment:

   #### On Windows
   ```
   $ python3 -m venv venv
   $ .\venv\Scripts\activate
   ```

   #### On macOS/Linux
   ```
   $ python3 -m venv venv
   $ source venv/bin/activate
   ```

4. Install the dependencies:

   ```
   $ pip install -r requirements.txt
   ```

### Execution

With the virtual environment activated, run:

   ```
   $ python3 main.py
   ```
   > **Note:** A `podcasts.db` file will be created in the same directory to store saved configurations.

### 🖥️ Interface Guide

1.  **Load Saved Podcast (Optional):** Select a podcast from the **"Saved Podcasts"** dropdown to automatically fill in its details (URL, folder, credentials).
2.  **Destination Folder:** If not loading, click **“Browse...”** and select where episodes will be saved.
3.  **Feed URL:** Paste the full RSS feed URL.
4.  **Podcast Name (for Saving):** Enter a unique name for this podcast configuration if you plan to save it. This field is required to **Save**.
5.  **Authentication (Optional):** Fill **User** and **Password** if the feed requires them.
6.  **Manage Configuration:**
    * **Save:** Click **"Save"** to store or update the current configuration (Name, URL, Folder, Credentials) in the database.
    * **Delete:** If a saved podcast is selected, click **"Delete"** to remove it permanently.
    * **Clear:** Click **"Clear"** to reset all form fields and the episode list.
7.  **Load Episodes:** Click **“Load episodes”** to fetch and list all episodes from the specified feed URL.
8.  **Search:** Use the **“Search...”** bar to filter episodes by title or description.
9.  **Sort:** Choose **“Order by”** to change the sorting mode (Newest/Oldest).
10. **Download:**
    * **Individual:** Click the green ⬇️ icon next to an episode.
    * **Batch:** Click the blue **“Download all”** button to download all *currently visible* episodes.
11. **List:** You can click a podcast to see a general info of it.

### 🪶 License

This project is licensed under the **GNU General Public License (GPL)**.
You are free to run, study, share, and modify the software, as long as any distributed version remains under the same license.
