import flet as ft
import threading
import xml.etree.ElementTree as ET
import requests
import html
import os
import sys
import urllib.parse
from time import sleep
import re

"""
    The purpose of this application is to list and download podcasts through a RSS Feed.
    You can download a single episode or download all the avaliable podcasts of the feed     Note: No optimization was made for many downloads at the same time. The download speed of the episodes may vary
    It is not possible to download any other kind of feed through it. Only podcast feeds are compatible.
    Tested URLS:
    - https://feeds.megaphone.fm/GLT1412515089       (The Joe Rogan Experience)
    - https://feeds.megaphone.fm/thispastweekend     (This Past Weekend w/ Theo Von)
    - https://feeds.megaphone.fm/MBS7713741099       (Congratulations with Chris D'Elia)
    - https://api.sacocheio.tv/rss/desinformacao     (Desinformacao Podcast)                  Note: this one has an user/password authentication
"""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/5.37.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/5.37.36"
}

def extract_episode_number(title_str):
    if not title_str:
        return 0
    match = re.search(r"^\s*?(\d+)|#(\d+)", title_str)
    if match:
        if match.group(1):
            return int(match.group(1))
        if match.group(2):
            return int(match.group(2))
    return 0


class EpisodeControl(ft.Container):
    
    def __init__(self, page: ft.Page, ep_number: int, title, description, image_src, download_url, filename, download_dir, 
                 global_cancel_event: threading.Event, 
                 global_controls: dict, 
                 episode_list_ref: ft.ListView):
        
        super().__init__()
        self.page = page
        self.ep_number = ep_number
        self.title = title
        self.description = description
        self.image_src = image_src
        self.download_url = download_url
        self.filename = filename
        self.download_dir = download_dir
        
        self.global_cancel_event = global_cancel_event
        self.individual_cancel_event = threading.Event()
        
        self.global_controls = global_controls
        self.episode_list_ref = episode_list_ref
        
        self.full_file_path = os.path.join(self.download_dir, self.filename)
        
        self.download_button = ft.IconButton(
            icon="download",
            tooltip="Download this episode",
            icon_color="green",
            on_click=self.individual_download_task
        )

        status_content = None
        if os.path.exists(self.full_file_path):
            status_content = ft.Icon(name="folder_zip", color="yellow")
        else:
            status_content = ft.Row(
                [self.download_button],
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            )

        initial_trailing_content = ft.Container(
            content=status_content,
            width=80,
            alignment=ft.alignment.center
        )

        self.trailing_control = ft.AnimatedSwitcher(
            content=initial_trailing_content,
            transition=ft.AnimatedSwitcherTransition.SCALE
        )
        
        self.content = ft.ListTile(
            leading=ft.Image(src=self.image_src, width=50, height=50, fit=ft.ImageFit.COVER, border_radius=5),
            title=ft.Text(self.title, weight="bold"),
            subtitle=ft.Text(self.description, max_lines=10, overflow=ft.TextOverflow.CLIP),
            trailing=self.trailing_control,
            expand=True
        )

    def _set_trailing(self, control):
        self.trailing_control.content = control
        try:
            self.update()
        except:
            pass 
    
    def _toggle_global_controls(self, state: bool):
        self.global_controls["btn_fetch_feed"].disabled = state
        self.global_controls["btn_start_download"].disabled = state
        self.global_controls["dd_sort"].disabled = state
        
        self.page.update()

    def individual_download_task(self, e):
        self.page.run_thread(self.run_individual_download)

    def run_individual_download(self):
        self._toggle_global_controls(True)
        try:
            self.download_logic(HEADERS, self.individual_cancel_event, show_cancel_button=True)
        finally:
            self._toggle_global_controls(False)

    def run_batch_download(self, headers):
        if not os.path.exists(self.full_file_path):
            self.download_logic(HEADERS, self.global_cancel_event, show_cancel_button=False)

    def download_logic(self, headers, cancel_event: threading.Event, show_cancel_button: bool):
        
        cancel_event.clear()
        progress_control = ft.ProgressRing(value=0, width=20, height=20, stroke_width=2, color="blue")
        
        if show_cancel_button:
            cancel_btn = ft.IconButton(
                icon="cancel", 
                icon_color="red",
                on_click=lambda _: cancel_event.set(),
                tooltip="Cancel download"
            )
            progress_row = ft.Row(
                [progress_control, cancel_btn], 
                spacing=5, 
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            )
            self._set_trailing(ft.Container(
                content=progress_row,
                width=80,
                alignment=ft.alignment.center
            ))
        else:
            self._set_trailing(ft.Container(
                content=progress_control, 
                alignment=ft.alignment.center, 
                width=80
            ))

        if os.path.exists(self.full_file_path):
            self._set_trailing(ft.Container(
                content=ft.Icon(name="folder_zip", color="yellow"),
                width=80,
                alignment=ft.alignment.center
            ))
            return

        try:
            with requests.get(self.download_url, headers=headers, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(self.full_file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): 
                        if cancel_event.is_set():
                            break
                        f.write(chunk)
                        
                        if total_size > 0:
                            downloaded_size += len(chunk)
                            progress_control.value = downloaded_size / total_size
                            self.update()
            
            if cancel_event.is_set():
                if os.path.exists(self.full_file_path):
                    os.remove(self.full_file_path)
                
                cancel_content = ft.Row(
                    [self.download_button], 
                    spacing=5, 
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER
                )
                self._set_trailing(ft.Container(
                    content=cancel_content,
                    width=80,
                    alignment=ft.alignment.center
                ))
            else:
                self._set_trailing(ft.Container(
                    content=ft.Icon(name="check_circle", color="green"),
                    width=80,
                    alignment=ft.alignment.center
                ))
                
        except Exception as e:
            if os.path.exists(self.full_file_path):
                os.remove(self.full_file_path)
            
            error_content = ft.Row(
                [ft.Icon(name="error", color="red"), self.download_button], 
                spacing=5, 
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            )
            self._set_trailing(ft.Container(
                content=error_content,
                width=80,
                alignment=ft.alignment.center
            ))


def main(page: ft.Page):
    page.title = "Podcast Downloader"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.padding = 10
    
    global_cancel_event = threading.Event()
    
    all_episode_controls_master = []

    def on_dialog_result(e: ft.FilePickerResultEvent):
        if e.path:
            txt_download_dir.value = e.path
            page.update()

    file_picker = ft.FilePicker(on_result=on_dialog_result)
    page.overlay.append(file_picker)

    def on_search(e):
        search_term = txt_search.value.lower().strip()
        
        if not all_episode_controls_master:
             if not search_term:
                 if not lv_episodes.controls or isinstance(lv_episodes.controls[0], ft.Text):
                      lv_episodes.controls = [ft.Text("Provide a feed URL and click 'Load episodes'.", color="grey")]
             page.update()
             return

        filtered_controls = []
        if not search_term:
            filtered_controls = all_episode_controls_master.copy()
        else:
            for control in all_episode_controls_master:
                title = control.title.lower()
                description = control.description.lower()
                
                if search_term in title or search_term in description:
                    filtered_controls.append(control)
        
        if not filtered_controls:
            lv_episodes.controls = [ft.Text("No episodes match your search.", color="grey", text_align=ft.TextAlign.CENTER)]
        else:
            lv_episodes.controls = filtered_controls
        
        page.update()

    def parse_feed_thread(final_rss_url, download_dir, sort_order):
        nonlocal all_episode_controls_master
        try:
            all_episode_controls_master = []
            lv_episodes.controls.clear()
            lv_episodes.controls.append(ft.Row([ft.ProgressRing(), ft.Text("Searching feed...")], alignment=ft.MainAxisAlignment.CENTER))
            page.update()

            rss_response = requests.get(final_rss_url, headers=HEADERS)
            rss_response.raise_for_status()
            rss_response.encoding = 'utf-8'
            xml_data = rss_response.text

            root = ET.fromstring(xml_data)
            items = root.findall('.//item')
            
            channel_image_tag = root.find('.//channel/image/url')
            channel_image = channel_image_tag.text if channel_image_tag is not None else ""

            all_episodes = []
            
            if not items:
                lv_episodes.controls.clear()
                lv_episodes.controls.append(ft.Text("No episodes were found on feed.", color="red"))
                btn_start_download.disabled = True
            else:
                global_controls_dict = {
                    "btn_fetch_feed": btn_fetch_feed,
                    "btn_start_download": btn_start_download,
                    "dd_sort": dd_sort
                }
                
                total_items = len(items)
                for i, item in enumerate(items):
                    title = item.findtext('title', 'No title')
                    description = item.findtext('description', 'No description')
                    enclosure = item.find('enclosure')
                    
                    ep_number = extract_episode_number(title)
                    fallback_number = total_items - i
                    final_ep_number = ep_number if ep_number > 0 else fallback_number
                    
                    if enclosure is not None and enclosure.get('url'):
                        raw_url = enclosure.get('url')
                        download_url = html.unescape(raw_url)
                        raw_filename = download_url.split('/')[-1].split('?')[0]
                        filename = urllib.parse.unquote(raw_filename)
                        
                        ep_control = EpisodeControl(
                            page, final_ep_number, title, description, channel_image,
                            download_url, filename, download_dir, 
                            global_cancel_event, 
                            global_controls_dict, 
                            lv_episodes 
                        )
                        all_episodes.append(ep_control)
                
                is_reversed = (sort_order == "DESC")
                all_episodes.sort(key=lambda x: x.ep_number, reverse=is_reversed)
                all_episode_controls_master = all_episodes
                lv_episodes.controls = all_episodes
                btn_start_download.disabled = False
            
            prog_bar_total.value = 0
            
        except Exception as e:
            lv_episodes.controls.clear()
            all_episode_controls_master = []
            lv_episodes.controls.append(ft.Text(f"Error while loading feed: {e}", color="red"))
            btn_start_download.disabled = True
            
        finally:
            btn_fetch_feed.disabled = False
            dd_sort.disabled = False
            on_search(None) 
            page.update()

    def run_all_downloads_thread(download_dir):
        try:
            all_episode_controls = [
                c for c in lv_episodes.controls 
                if isinstance(c, EpisodeControl)
            ]
            total = len(all_episode_controls)
            
            for i, ep_control in enumerate(all_episode_controls):
                if global_cancel_event.is_set():
                    if not os.path.exists(ep_control.full_file_path):
                        cancel_content = ft.Row(
                            [ep_control.download_button], 
                            spacing=5, 
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            alignment=ft.MainAxisAlignment.CENTER
                        )
                        ep_control._set_trailing(ft.Container(
                            content=cancel_content,
                            width=80,
                            alignment=ft.alignment.center
                        ))
                    continue
                
                ep_control.run_batch_download(HEADERS)
                
                prog_bar_total.value = (i + 1) / total
                page.update()

        except Exception as e:
            print(f"Error on the download loop: {e}")
        finally:
            btn_start_download.visible = True
            btn_cancel_download.visible = False
            btn_fetch_feed.disabled = False
            dd_sort.disabled = False
            
            page.update()

    def fetch_feed_clicked(e):
        rss_url_input = txt_rss_url.value.strip()
        username = txt_username.value.strip()
        password = txt_password.value
        download_dir = txt_download_dir.value

        if not rss_url_input or not download_dir:
            lv_episodes.controls.clear()
            all_episode_controls_master = []
            lv_episodes.controls.append(ft.Text("Error: Provide an URL and a directory", color="red"))
            page.update()
            return

        clean_url = rss_url_input.removeprefix("https://").removeprefix("http://")

        final_rss_url = ""
        if username and password:
            safe_user = urllib.parse.quote(username)
            safe_pass = urllib.parse.quote(password)
            final_rss_url = f"https://{safe_user}:{safe_pass}@{clean_url}"
        else:
            final_rss_url = f"https://{clean_url}"
        
        btn_fetch_feed.disabled = True
        btn_start_download.disabled = True
        dd_sort.disabled = True
        page.update()
        
        page.run_thread(parse_feed_thread, final_rss_url, download_dir, dd_sort.value)

    def start_download_clicked(e):
        download_dir = txt_download_dir.value
        if not download_dir:
             lv_episodes.controls.clear()
             all_episode_controls_master = []
             lv_episodes.controls.append(ft.Text("Error: Select a directory to save.", color="red"))
             page.update()
             return

        global_cancel_event.clear()
        btn_start_download.visible = False
        btn_cancel_download.visible = True
        btn_fetch_feed.disabled = True
        dd_sort.disabled = True
        
        for control in lv_episodes.controls:
            if isinstance(control, EpisodeControl):
                if not os.path.exists(control.full_file_path):
                    schedule_icon = ft.Container(
                        content=ft.Icon(name="schedule", color="grey"),
                        width=80,
                        alignment=ft.alignment.center
                    )
                    control._set_trailing(schedule_icon)
        
        page.update()
        page.run_thread(run_all_downloads_thread, download_dir)

    def cancel_download_clicked(e):
        global_cancel_event.set()
    
    def sort_list_changed(e):
        if not all_episode_controls_master:
            return 

        is_reversed = (dd_sort.value == "DESC")
        all_episode_controls_master.sort(key=lambda x: x.ep_number, reverse=is_reversed)
        
        on_search(None)

    txt_rss_url = ft.TextField(label="Feed URL (ex. api.rssfeed.com/rss/feed)", autofocus=True, expand=True)
    txt_username = ft.TextField(label="User (Optional)", expand=1)
    txt_password = ft.TextField(label="Password (Optional)", password=True, can_reveal_password=True, expand=1)
    
    txt_download_dir = ft.TextField(label="Save to:", read_only=True, expand=True)
    btn_browse = ft.ElevatedButton(
        "Procurar...",
        icon="folder_open",
        on_click=lambda _: file_picker.get_directory_path()
    )
    
    dd_sort = ft.Dropdown(
        label="Order by",
        options=[
            ft.dropdown.Option(key="DESC", text="Newest (Desc)"),
            ft.dropdown.Option(key="ASC", text="Oldest (Asc)"),
        ],
        value="DESC",
        on_change=sort_list_changed,
        width=240,
        disabled=True
    )

    btn_fetch_feed = ft.ElevatedButton(
        "Load episodes",
        icon="refresh",
        on_click=fetch_feed_clicked,
        expand=1
    )
    btn_start_download = ft.ElevatedButton(
        "Download all",
        icon="download",
        on_click=start_download_clicked,
        bgcolor="blue_700",
        color="white",
        expand=1,
        disabled=True
    )
    btn_cancel_download = ft.ElevatedButton(
        "Cancel",
        icon="cancel",
        on_click=cancel_download_clicked,
        bgcolor="red_700",
        color="white",
        expand=1,
        visible=False
    )

    prog_bar_total = ft.ProgressBar(value=0)

    txt_search = ft.TextField(
        label="Search by title or description...", 
        on_change=on_search, 
        expand=True, 
        prefix_icon=ft.Icons.SEARCH
    )

    lv_episodes = ft.ListView(
        [ft.Text("Provide a feed URL and click 'Load episodes'.", color="grey")],
        expand=True,
        spacing=10
    )

    page.add(
        ft.Column(
            [
                ft.Row([txt_rss_url]),
                ft.Row([txt_username, txt_password]),
                ft.Row([txt_download_dir, btn_browse]),
                ft.Row([
                    btn_fetch_feed,
                    dd_sort
                ]),
                ft.Row([
                    ft.Stack([btn_start_download, btn_cancel_download], expand=1)
                ]),
                ft.Row([txt_search]),
                prog_bar_total,
                lv_episodes,
            ],
            expand=True
        )
    )

if __name__ == "__main__":
    ft.app(target=main)