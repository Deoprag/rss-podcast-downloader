import flet as ft
import threading
import xml.etree.ElementTree as ET
import requests
import html
import os
import urllib.parse
from time import sleep
import re
import sqlite3

from . import data_manager as db
from .ui_components import EpisodeControl
from .utils import HEADERS, extract_episode_number


ui_refs = {}
all_episode_controls_master = []
global_cancel_event = threading.Event()

def update_sidebar(episode_control=None):
    sidebar = ui_refs.get("sidebar_column")
    title_text = ui_refs.get("sidebar_title")
    image_display = ui_refs.get("sidebar_image")
    pub_date_text = ui_refs.get("sidebar_pub_date")
    duration_text = ui_refs.get("sidebar_duration")
    author_text = ui_refs.get("sidebar_author")
    link_text = ui_refs.get("sidebar_link")
    description_text = ui_refs.get("sidebar_description")

    if not sidebar or not title_text or not image_display or not description_text or \
       not pub_date_text or not duration_text or not author_text or not link_text:
        return

    if episode_control is None:
        sidebar.visible = False
    else:
        title_text.value = episode_control.title
        image_display.src = episode_control.image_src
        pub_date_text.value = f"{episode_control.pub_date}" if episode_control.pub_date else "N/A"
        duration_text.value = f"{episode_control.duration}" if episode_control.duration else "N/A"
        author_text.value = f"{episode_control.author}" if episode_control.author else "N/A"
        link_text.value = f"{episode_control.link}" if episode_control.link else "N/A"
        link_text.visible = bool(episode_control.link)
        link_text.parent.visible = bool(episode_control.link)
        
        description_text.value = episode_control.description
        sidebar.visible = True

    sidebar.update()

def close_sidebar(e):
    update_sidebar(None)

def show_snackbar(message, color="green"):
    ui_refs["snack_bar"].content = ft.Text(message)
    ui_refs["snack_bar"].bgcolor = color
    ui_refs["snack_bar"].open = True
    ui_refs["page"].update()

def clear_form():
    global all_episode_controls_master
    all_episode_controls_master = []

    ui_refs["dd_podcasts"].value = None
    ui_refs["txt_podcast_name"].value = ""
    ui_refs["txt_rss_url"].value = ""
    ui_refs["txt_username"].value = ""
    ui_refs["txt_password"].value = ""
    ui_refs["txt_download_dir"].value = ""
    ui_refs["txt_search"].value = ""

    ui_refs["lv_episodes"].controls = [ft.Text("Select or fill in a podcast configuration.", color="grey")]
    ui_refs["btn_delete_podcast"].disabled = True
    ui_refs["btn_start_download"].disabled = True
    ui_refs["dd_sort"].disabled = True
    ui_refs["prog_bar_total"].value = 0

    update_sidebar(None)

def clear_form_clicked(e):
    clear_form()
    ui_refs["page"].update()


def load_saved_podcasts():
    dropdown = ui_refs["dd_podcasts"]
    dropdown.options = [ft.dropdown.Option(key=None, text="Select a saved podcast...", disabled=True)]
    try:
        podcasts = db.db_get_podcasts()
        for podcast_id, podcast_name in podcasts:
            dropdown.options.append(
                ft.dropdown.Option(key=podcast_id, text=podcast_name)
            )
    except Exception as e:
        show_snackbar(f"Error loading podcasts: {e}", "red")

def on_podcast_selected(e):
    podcast_id = e.control.value
    if podcast_id is None:
        if ui_refs["txt_podcast_name"].value:
             clear_form()
             ui_refs["page"].update()
        return

    try:
        details = db.db_get_podcast_details(podcast_id)
        if details:
            ui_refs["txt_podcast_name"].value = details["name"]
            ui_refs["txt_rss_url"].value = details["feed_url"]
            ui_refs["txt_download_dir"].value = details["download_dir"]
            ui_refs["txt_username"].value = details["username"] if details["username"] else ""
            ui_refs["txt_password"].value = details["password"] if details["password"] else ""

            ui_refs["btn_delete_podcast"].disabled = False
            global all_episode_controls_master
            all_episode_controls_master = []
            ui_refs["lv_episodes"].controls = [ft.Text("Click 'Load episodes' to fetch.", color="grey")]
            ui_refs["btn_start_download"].disabled = True
            ui_refs["dd_sort"].disabled = True
            ui_refs["prog_bar_total"].value = 0
            update_sidebar(None)

    except Exception as e:
        show_snackbar(f"Error loading details: {e}", "red")
    ui_refs["page"].update()

def save_podcast_clicked(e):
    name = ui_refs["txt_podcast_name"].value.strip()
    url = ui_refs["txt_rss_url"].value.strip()
    dir_path = ui_refs["txt_download_dir"].value.strip()

    if not name or not url or not dir_path:
        show_snackbar("Name, Feed URL, and Save directory are required.", "red")
        return

    user = ui_refs["txt_username"].value.strip()
    pwd = ui_refs["txt_password"].value

    try:
        db.db_save_podcast(name, url, dir_path, user, pwd)
        current_selection_text = name
        load_saved_podcasts()
        show_snackbar(f"Podcast '{name}' saved successfully!")

        new_key = None
        for option in ui_refs["dd_podcasts"].options:
            if option.text == current_selection_text:
                new_key = option.key
                break
        if new_key is not None:
             ui_refs["dd_podcasts"].value = new_key

        ui_refs["btn_delete_podcast"].disabled = (new_key is None)

    except sqlite3.IntegrityError:
         show_snackbar(f"Error: Podcast name '{name}' already exists.", "red")
    except Exception as e:
        show_snackbar(f"Error saving podcast: {e}", "red")
    ui_refs["page"].update()

def delete_podcast_clicked(e):
    podcast_id = ui_refs["dd_podcasts"].value
    if podcast_id is None:
        show_snackbar("No podcast selected to delete.", "red")
        return

    try:
        podcast_name = ui_refs["txt_podcast_name"].value
        db.db_delete_podcast(podcast_id)
        show_snackbar(f"Podcast '{podcast_name}' deleted successfully.")
        clear_form()
        load_saved_podcasts()
    except Exception as e:
        show_snackbar(f"Error deleting podcast: {e}", "red")
    ui_refs["page"].update()


def fetch_feed_clicked(e):
    rss_url_input = ui_refs["txt_rss_url"].value.strip()
    download_dir = ui_refs["txt_download_dir"].value.strip()
    username = ui_refs["txt_username"].value.strip()
    password = ui_refs["txt_password"].value

    if not rss_url_input or not download_dir:
        show_snackbar("Error: Feed URL and Save directory are required.", "red")
        return

    clean_url = rss_url_input.removeprefix("https://").removeprefix("http://")
    final_rss_url = ""
    if username and password:
        safe_user = urllib.parse.quote(username)
        safe_pass = urllib.parse.quote(password)
        final_rss_url = f"https://{safe_user}:{safe_pass}@{clean_url}"
    else:
        if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
             final_rss_url = f"https://{clean_url}"
        else:
             final_rss_url = rss_url_input

    ui_refs["btn_fetch_feed"].disabled = True
    ui_refs["btn_start_download"].disabled = True
    ui_refs["dd_sort"].disabled = True
    ui_refs["page"].update()

    ui_refs["page"].run_thread(
        parse_feed_thread,
        final_rss_url,
        download_dir,
        ui_refs["dd_sort"].value
    )

def parse_feed_thread(final_rss_url, download_dir, sort_order):
    global all_episode_controls_master
    try:
        all_episode_controls_master = []
        ui_refs["lv_episodes"].controls = [ft.Row([ft.ProgressRing(), ft.Text("Searching feed...")], alignment=ft.MainAxisAlignment.CENTER)]
        ui_refs["page"].update()

        rss_response = requests.get(final_rss_url, headers=HEADERS, timeout=15)
        rss_response.raise_for_status()
        rss_response.encoding = rss_response.apparent_encoding if rss_response.apparent_encoding else 'utf-8'
        xml_data = rss_response.text

        namespaces = {
            'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
            'content': 'http://purl.org/rss/1.0/modules/content/'
        }

        root = ET.fromstring(xml_data)
        items = root.findall('.//item')

        if not ui_refs["txt_podcast_name"].value.strip():
            try:
                channel_title = root.find('.//channel/title').text
                if channel_title:
                    ui_refs["txt_podcast_name"].value = channel_title.strip()
            except Exception:
                pass

        channel_image_tag = root.find('.//channel/image/url')
        itunes_image_tag = root.find('.//channel/itunes:image', namespaces)
        channel_image = ""
        if channel_image_tag is not None and channel_image_tag.text:
             channel_image = channel_image_tag.text
        elif itunes_image_tag is not None and itunes_image_tag.get('href'):
             channel_image = itunes_image_tag.get('href')

        all_episodes = []

        if not items:
            ui_refs["lv_episodes"].controls = [ft.Text("No episodes were found in this feed.", color="red")]
            ui_refs["btn_start_download"].disabled = True
        else:
            global_controls_dict = {
                "btn_fetch_feed": ui_refs["btn_fetch_feed"],
                "btn_start_download": ui_refs["btn_start_download"],
                "dd_sort": ui_refs["dd_sort"]
            }

            total_items = len(items)
            for i, item in enumerate(items):

                title = item.findtext('title', 'No Title') or 'No Title'

                description_raw = item.findtext('description', None)
                if description_raw is None:
                    description_raw = item.findtext('itunes:summary', namespaces, None)
                if description_raw is None:
                    description_raw = item.findtext('content:encoded', namespaces, '')

                description_str = description_raw if description_raw is not None else ''

                description_no_html = re.sub('<[^<]+?>', '', description_str)
                description_clean = html.unescape(description_no_html).strip()

                pub_date_str = item.findtext('pubDate', 'N/A') or 'N/A'
                link = item.findtext('link', '') or ''
                guid = item.findtext('guid', '') or ''
                duration_tag = item.find('itunes:duration', namespaces)
                duration = duration_tag.text if duration_tag is not None else ''
                author_tag = item.find('itunes:author', namespaces)
                author = author_tag.text if author_tag is not None else ''

                enclosure = item.find('enclosure')
                enclosure_url = enclosure.get('url') if enclosure is not None else None
                enclosure_type = enclosure.get('type', '') if enclosure is not None else ''

                ep_image_tag = item.find('itunes:image', namespaces)
                image_src = channel_image
                if ep_image_tag is not None:
                    href = ep_image_tag.get('href')
                    if href:
                        image_src = href

                ep_number = extract_episode_number(title)
                fallback_number = total_items - i
                final_ep_number = ep_number if ep_number > 0 else fallback_number

                if enclosure is not None and enclosure_url and enclosure_type.startswith('audio'):
                    download_url = html.unescape(enclosure_url)

                    raw_filename = download_url.split('/')[-1].split('?')[0]
                    filename = urllib.parse.unquote(raw_filename)
                    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
                    filename = filename.strip()

                    if not filename:
                        filename = f"episode_{final_ep_number}.mp3"

                    ep_control = EpisodeControl(
                        page = ui_refs["page"],
                        ep_number = final_ep_number,
                        title = title,
                        description = description_clean,
                        image_src = image_src,
                        download_url = download_url,
                        filename = filename,
                        download_dir = download_dir,
                        global_cancel_event = global_cancel_event,
                        global_controls = global_controls_dict,
                        episode_list_ref = ui_refs["lv_episodes"],
                        pub_date = pub_date_str,
                        link = link,
                        duration = duration,
                        author = author,
                        guid = guid
                    )

                    all_episodes.append(ep_control)
                else:
                    print(f"Item {i}: Ignored (no valid audio enclosure).")

            if not all_episodes:
                 ui_refs["lv_episodes"].controls = [ft.Text("No valid audio episodes found.", color="orange")]
                 ui_refs["btn_start_download"].disabled = True
            else:
                 is_reversed = (sort_order == "DESC")
                 all_episodes.sort(key=lambda x: x.ep_number, reverse=is_reversed)

                 all_episode_controls_master = all_episodes
                 ui_refs["lv_episodes"].controls = all_episodes

                 ui_refs["btn_start_download"].disabled = False

        ui_refs["prog_bar_total"].value = 0

    except requests.exceptions.RequestException as e:
         ui_refs["lv_episodes"].controls = [ft.Text(f"Network Error: {e}", color="red")]
         ui_refs["btn_start_download"].disabled = True
    except ET.ParseError as e:
        ui_refs["lv_episodes"].controls = [ft.Text(f"Feed Format Error: {e}", color="red")]
        ui_refs["btn_start_download"].disabled = True
    except Exception as e:
        import traceback
        traceback.print_exc()
        ui_refs["lv_episodes"].controls = [ft.Text(f"Error loading feed: {e}", color="red")]
        ui_refs["btn_start_download"].disabled = True
    finally:
        ui_refs["btn_fetch_feed"].disabled = False
        ui_refs["dd_sort"].disabled = not bool(all_episode_controls_master)
        on_search(None)
        try:
             ui_refs["page"].update()
        except Exception:
             pass
        
def on_search(e):
    search_term = ui_refs["txt_search"].value.lower().strip()

    if not all_episode_controls_master:
         if not search_term:
             if not ui_refs["lv_episodes"].controls or isinstance(ui_refs["lv_episodes"].controls[0], ft.Text):
                  ui_refs["lv_episodes"].controls = [ft.Text("Select or fill in a podcast configuration.", color="grey")]
         else:
              ui_refs["lv_episodes"].controls = [ft.Text("No episodes loaded to search.", color="grey", text_align=ft.TextAlign.CENTER)]
         ui_refs["page"].update()
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
        ui_refs["lv_episodes"].controls = [ft.Text("No episodes match your search.", color="grey", text_align=ft.TextAlign.CENTER)]
    else:
        new_list_controls_with_dividers = []
        num_filtered = len(filtered_controls)
        for i, episode_control in enumerate(filtered_controls):
            new_list_controls_with_dividers.append(episode_control)
            if i < num_filtered - 1:
                 new_list_controls_with_dividers.append(
                     ft.Divider(height=1, color=ft.Colors.with_opacity(0.5, ft.Colors.GREY))
                 )
        ui_refs["lv_episodes"].controls = new_list_controls_with_dividers

    ui_refs["page"].update()

def sort_list_changed(e):
    if not all_episode_controls_master:
        return

    is_reversed = (ui_refs["dd_sort"].value == "DESC")
    all_episode_controls_master.sort(key=lambda x: x.ep_number, reverse=is_reversed)

    on_search(None)

def start_download_clicked(e):
    download_dir = ui_refs["txt_download_dir"].value.strip()
    if not download_dir:
         show_snackbar("Error: Select a directory to save.", "red")
         return

    global_cancel_event.clear()

    ui_refs["btn_start_download"].visible = False
    ui_refs["btn_cancel_download"].visible = True
    ui_refs["btn_fetch_feed"].disabled = True
    ui_refs["dd_sort"].disabled = True

    items_to_download = 0
    for control in ui_refs["lv_episodes"].controls:
        if isinstance(control, EpisodeControl):
            if not os.path.exists(control.full_file_path):
                schedule_icon = ft.Container(
                    content=ft.Icon(name=ft.Icons.SCHEDULE, color=ft.Colors.GREY),
                    width=80,
                    alignment=ft.alignment.center
                )
                control._set_trailing(schedule_icon)
                items_to_download += 1

    if items_to_download == 0:
        show_snackbar("All visible episodes are already downloaded or list is empty.", "blue")
        ui_refs["btn_start_download"].visible = True
        ui_refs["btn_cancel_download"].visible = False
        ui_refs["btn_fetch_feed"].disabled = False
        ui_refs["dd_sort"].disabled = False
        ui_refs["page"].update()
        return

    ui_refs["page"].update()
    ui_refs["page"].run_thread(run_all_downloads_thread, download_dir)

def cancel_download_clicked(e):
    global_cancel_event.set()
    show_snackbar("Cancellation requested...", "orange")

def run_all_downloads_thread(download_dir):
    try:
        episode_controls_to_download = [
            c for c in ui_refs["lv_episodes"].controls
            if isinstance(c, EpisodeControl)
        ]

        items_in_queue = [
            ep for ep in episode_controls_to_download
            if not os.path.exists(ep.full_file_path)
        ]

        total_to_download = len(items_in_queue)
        completed_count = 0

        for i, ep_control in enumerate(items_in_queue):
            if global_cancel_event.is_set():
                show_snackbar("Batch download cancelled.", "red")
                for remaining_ep in items_in_queue[i:]:
                     cancel_content = ft.Row([remaining_ep.download_button], spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)
                     remaining_ep._set_trailing(ft.Container(content=cancel_content, width=80, alignment=ft.alignment.center))
                break

            ep_control.run_batch_download(HEADERS)
            completed_count = i + 1

            if total_to_download > 0:
                ui_refs["prog_bar_total"].value = completed_count / total_to_download
                try:
                     ui_refs["page"].update()
                except Exception:
                     break

        if not global_cancel_event.is_set() and total_to_download > 0:
            show_snackbar("All downloads complete!", "green")


    except Exception as e:
        print(f"Error during batch download loop: {e}")
        show_snackbar(f"Error during download: {e}", "red")
    finally:
        ui_refs["btn_start_download"].visible = True
        ui_refs["btn_cancel_download"].visible = False
        ui_refs["btn_fetch_feed"].disabled = False
        ui_refs["dd_sort"].disabled = not not all_episode_controls_master

        if global_cancel_event.is_set():
             if total_to_download > 0:
                  ui_refs["prog_bar_total"].value = completed_count / total_to_download
             else:
                  ui_refs["prog_bar_total"].value = 0.0
        elif total_to_download > 0:
             ui_refs["prog_bar_total"].value = 1.0
        else:
             ui_refs["prog_bar_total"].value = 0.0

        try:
             ui_refs["page"].update()
        except Exception:
             pass