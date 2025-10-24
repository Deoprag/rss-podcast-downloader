import flet as ft
import threading

from podcast_downloader import data_manager as db
from podcast_downloader import app as logic
from podcast_downloader.ui_components import EpisodeControl
from podcast_downloader import utils

def main(page: ft.Page):
    page.title = "Podcast Downloader"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.padding = 10

    db.db_init()

    logic.ui_refs = {
        "page": page,
    }

    snack_bar = ft.SnackBar(content=ft.Text(""), bgcolor="green")
    page.snack_bar = snack_bar
    logic.ui_refs["snack_bar"] = snack_bar

    file_picker = ft.FilePicker(on_result=lambda e: on_dialog_result(e))
    page.overlay.append(file_picker)
    def on_dialog_result(e: ft.FilePickerResultEvent):
        if e.path:
            txt_download_dir.value = e.path
            page.update()

    dd_podcasts = ft.Dropdown(
        label="Saved Podcasts",
        options=[ft.dropdown.Option(key=None, text="Select a saved podcast...", disabled=True)],
        on_change=logic.on_podcast_selected,
        expand=True
    )
    logic.ui_refs["dd_podcasts"] = dd_podcasts

    txt_podcast_name = ft.TextField(
        label="Podcast Name (for saving)",
        expand=True
    )
    logic.ui_refs["txt_podcast_name"] = txt_podcast_name

    txt_rss_url = ft.TextField(label="Feed URL", expand=True)
    logic.ui_refs["txt_rss_url"] = txt_rss_url

    txt_username = ft.TextField(label="User (Optional)", expand=1)
    logic.ui_refs["txt_username"] = txt_username

    txt_password = ft.TextField(label="Password (Optional)", password=True, can_reveal_password=True, expand=1)
    logic.ui_refs["txt_password"] = txt_password

    txt_download_dir = ft.TextField(label="Save to:", read_only=True, expand=True)
    logic.ui_refs["txt_download_dir"] = txt_download_dir

    btn_browse = ft.ElevatedButton(
        "Browse...",
        icon=ft.Icons.FOLDER_OPEN,
        on_click=lambda _: file_picker.get_directory_path()
    )

    btn_save_podcast = ft.ElevatedButton(
        "Save", icon=ft.Icons.SAVE, on_click=logic.save_podcast_clicked,
        expand=1, tooltip="Save or Update podcast config by Name"
    )
    logic.ui_refs["btn_save_podcast"] = btn_save_podcast

    btn_delete_podcast = ft.ElevatedButton(
        "Delete", icon=ft.Icons.DELETE_FOREVER, on_click=logic.delete_podcast_clicked,
        expand=1, disabled=True, color="red", tooltip="Delete selected podcast"
    )
    logic.ui_refs["btn_delete_podcast"] = btn_delete_podcast

    btn_clear_form = ft.ElevatedButton(
        "Clear", icon=ft.Icons.CLEAR, on_click=logic.clear_form_clicked,
        expand=1, tooltip="Clear all fields"
    )
    logic.ui_refs["btn_clear_form"] = btn_clear_form

    dd_sort = ft.Dropdown(
        label="Order by",
        options=[
            ft.dropdown.Option(key="DESC", text="Newest (Desc)"),
            ft.dropdown.Option(key="ASC", text="Oldest (Asc)"),
        ],
        value="DESC",
        on_change=logic.sort_list_changed,
        width=240,
        disabled=True
    )
    logic.ui_refs["dd_sort"] = dd_sort

    btn_fetch_feed = ft.ElevatedButton(
        "Load episodes", icon=ft.Icons.REFRESH, on_click=logic.fetch_feed_clicked,
        expand=1
    )
    logic.ui_refs["btn_fetch_feed"] = btn_fetch_feed

    btn_start_download = ft.ElevatedButton(
        "Download all", icon=ft.Icons.DOWNLOAD, on_click=logic.start_download_clicked,
        bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE, expand=1, disabled=True
    )
    logic.ui_refs["btn_start_download"] = btn_start_download

    btn_cancel_download = ft.ElevatedButton(
        "Cancel", icon=ft.Icons.CANCEL, on_click=logic.cancel_download_clicked,
        bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE, expand=1, visible=False
    )
    logic.ui_refs["btn_cancel_download"] = btn_cancel_download

    prog_bar_total = ft.ProgressBar(value=0, height=10)
    logic.ui_refs["prog_bar_total"] = prog_bar_total

    txt_search = ft.TextField(
        label="Search by title or description...",
        on_change=logic.on_search,
        expand=True,
        prefix_icon=ft.Icons.SEARCH,
    )
    logic.ui_refs["txt_search"] = txt_search

    lv_episodes = ft.ListView(
        [ft.Text("Select or fill in a podcast configuration.", color="grey")],
        expand=True,
        spacing=0,
    )
    logic.ui_refs["lv_episodes"] = lv_episodes

    sidebar_title = ft.Text("", weight="bold", size=16, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)
    sidebar_image = ft.Image(src="", height=200, fit=ft.ImageFit.CONTAIN, border_radius=5)
    sidebar_pub_date = ft.Text("", size=14, selectable=True)
    sidebar_duration = ft.Text("", size=14, selectable=True)
    sidebar_author = ft.Text("", size=14, selectable=True, italic=True)
    sidebar_link = ft.Text("", size=14, selectable=True, italic=True)
    sidebar_description = ft.Text("", selectable=True)

    sidebar_column = ft.Column(
        [
            ft.Row(
                [
                    sidebar_title,
                    ft.IconButton(ft.Icons.CLOSE, tooltip="Close details", on_click=logic.close_sidebar)
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            ft.Divider(height=5),
            sidebar_image,
            ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
            ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH, size=14), sidebar_pub_date]),
            ft.Row([ft.Icon(ft.Icons.TIMER_OUTLINED, size=14), sidebar_duration]),
            ft.Row([ft.Icon(ft.Icons.PERSON_OUTLINE, size=14), sidebar_author]),
            ft.Row([ft.Icon(ft.Icons.LINK, size=14), sidebar_link]),
            ft.Divider(height=10),
            ft.Row([
                ft.Container(
                    content=ft.Column(
                        [sidebar_description],
                        scroll=ft.ScrollMode.AUTO,
                        alignment=ft.MainAxisAlignment.START,
                        expand=True
                    ),
                    expand=True,
                    padding=ft.padding.only(top=5),
                    alignment=ft.alignment.top_left
                ),
            ],
            expand=True
            )
            
        ],
        expand=False,
        visible=False,
        width=350,
        spacing=5,
        alignment=ft.MainAxisAlignment.START
    )

    logic.ui_refs["sidebar_column"] = sidebar_column
    logic.ui_refs["sidebar_title"] = sidebar_title
    logic.ui_refs["sidebar_image"] = sidebar_image
    logic.ui_refs["sidebar_pub_date"] = sidebar_pub_date
    logic.ui_refs["sidebar_duration"] = sidebar_duration
    logic.ui_refs["sidebar_author"] = sidebar_author
    logic.ui_refs["sidebar_link"] = sidebar_link
    logic.ui_refs["sidebar_description"] = sidebar_description
    logic.load_saved_podcasts()

    main_content_column = ft.Column(
            [
                ft.Row([dd_podcasts]),
                ft.Row([txt_podcast_name]),
                ft.Row([txt_rss_url]),
                ft.Row([txt_username, txt_password]),
                ft.Row([txt_download_dir, btn_browse]),
                ft.Row([btn_save_podcast, btn_delete_podcast, btn_clear_form]),
                ft.Divider(height=15, thickness=2),
                ft.Row([
                    btn_fetch_feed,
                    dd_sort
                ]),
                ft.Row(
                    [
                        ft.Stack([btn_start_download, btn_cancel_download])
                    ]
                ),
                ft.Row([txt_search]),
                prog_bar_total,
                lv_episodes,
            ],
            expand=True,
        )

    page.add(
        ft.Row(
            [
                main_content_column,
                ft.VerticalDivider(width=1),
                sidebar_column
            ],
            expand=True
        )
    )

if __name__ == "__main__":
    ft.app(target=main)