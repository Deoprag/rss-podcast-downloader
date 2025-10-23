import flet as ft
import threading
import requests
import html
import os
from time import sleep

from .utils import HEADERS
from . import app as logic

class EpisodeControl(ft.Container):
    """
    A custom Flet control representing a single podcast episode in the list.
    Manages its own download state and UI updates. Triggers sidebar display on click.
    """
    def __init__(self, page: ft.Page, ep_number: int, title, description, image_src, download_url, filename, download_dir,
                 global_cancel_event: threading.Event,
                 global_controls: dict,
                 episode_list_ref: ft.ListView,
                 pub_date: str,
                 link: str,
                 duration: str,
                 author: str,
                 guid: str):

        super().__init__()

        self.page = page
        self.ep_number = ep_number
        self.title = title
        self.description = description
        self.image_src = image_src
        self.download_url = download_url
        self.filename = filename
        self.download_dir = download_dir

        self.pub_date = pub_date
        self.link = link
        self.duration = duration
        self.author = author
        self.guid = guid

        self.global_cancel_event = global_cancel_event
        self.individual_cancel_event = threading.Event()

        self.global_controls = global_controls
        self.episode_list_ref = episode_list_ref

        self.full_file_path = os.path.join(self.download_dir, self.filename)

        self.download_button = ft.IconButton(
            icon=ft.Icons.DOWNLOAD,
            tooltip="Download this episode",
            icon_color=ft.Colors.GREEN,
            on_click=self.individual_download_task_prevent_sidebar
        )

        status_content = None
        if os.path.exists(self.full_file_path):
            status_content = ft.Icon(name=ft.Icons.FOLDER_ZIP, color=ft.Colors.YELLOW)
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

        self.list_tile = ft.ListTile(
            leading=ft.Image(
                src=self.image_src,
                width=80,
                height=80,
                fit=ft.ImageFit.COVER,
                border_radius=5
            ),
            title=ft.Text(self.title, weight="bold", max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
            subtitle=ft.Text(self.description, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
            trailing=self.trailing_control
        )

        self.content = ft.Container(
            content=self.list_tile,
            height=110,
            border_radius=5,
            ink=True,
            on_click=self.handle_click
        )

    def handle_click(self, e):
        logic.update_sidebar(self)

    def individual_download_task_prevent_sidebar(self, e):
        e.cancel = True
        self.individual_download_task(e)

    def _set_trailing(self, control):
        self.trailing_control.content = control
        try:
            self.update()
        except Exception:
            pass

    def _toggle_global_controls(self, state: bool):
        self.global_controls["btn_fetch_feed"].disabled = state
        self.global_controls["btn_start_download"].disabled = state
        self.global_controls["dd_sort"].disabled = state
        try:
            self.page.update()
        except Exception:
            pass

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
            self.download_logic(headers, self.global_cancel_event, show_cancel_button=False)

    def download_logic(self, headers, cancel_event: threading.Event, show_cancel_button: bool):
        cancel_event.clear()
        progress_control = ft.ProgressRing(value=0, width=20, height=20, stroke_width=3, color=ft.Colors.BLUE)

        if show_cancel_button:
            cancel_btn = ft.IconButton(
                icon=ft.Icons.CANCEL,
                icon_color=ft.Colors.RED,
                on_click=lambda _: cancel_event.set(),
                tooltip="Cancel download"
            )
            progress_row = ft.Row(
                [progress_control, cancel_btn],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            )
            self._set_trailing(ft.Container(content=progress_row, width=80, alignment=ft.alignment.center))
        else:
            self._set_trailing(ft.Container(content=progress_control, alignment=ft.alignment.center, width=80))

        if os.path.exists(self.full_file_path):
            self._set_trailing(ft.Container(content=ft.Icon(name=ft.Icons.FOLDER_ZIP, color=ft.Colors.YELLOW), width=80, alignment=ft.alignment.center))
            return

        try:
            with requests.get(self.download_url, headers=headers, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded_size = 0

                os.makedirs(self.download_dir, exist_ok=True)

                with open(self.full_file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if cancel_event.is_set():
                            break
                        f.write(chunk)

                        if total_size > 0:
                            downloaded_size += len(chunk)
                            new_value = downloaded_size / total_size
                            progress_control.value = min(new_value, 1.0)
                            try:
                                self.update()
                            except Exception:
                                break

            if cancel_event.is_set():
                if os.path.exists(self.full_file_path):
                    try:
                        os.remove(self.full_file_path)
                    except OSError as e:
                        print(f"Error removing cancelled file {self.full_file_path}: {e}")
                cancel_content = ft.Row([self.download_button], spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)
                self._set_trailing(ft.Container(content=cancel_content, width=80, alignment=ft.alignment.center))
            elif (total_size > 0 and downloaded_size >= total_size) or (total_size == 0 and downloaded_size > 0 and os.path.exists(self.full_file_path)):
                 self._set_trailing(ft.Container(content=ft.Icon(name=ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN), width=80, alignment=ft.alignment.center))
            else:
                 if os.path.exists(self.full_file_path):
                     try:
                        os.remove(self.full_file_path)
                     except OSError as e:
                         print(f"Error removing incomplete file {self.full_file_path}: {e}")
                 raise IOError("Download incomplete or failed without explicit cancel.")

        except Exception as e:
            print(f"Error downloading {self.filename}: {e}")
            if os.path.exists(self.full_file_path):
                 try:
                    os.remove(self.full_file_path)
                 except OSError as err:
                     print(f"Error removing failed download file {self.full_file_path}: {err}")
            error_content = ft.Row([ft.Icon(name=ft.Icons.ERROR, color=ft.Colors.RED), self.download_button], spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)
            self._set_trailing(ft.Container(content=error_content, width=80, alignment=ft.alignment.center))