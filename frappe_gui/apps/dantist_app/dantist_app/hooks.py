app_name = "dantist_app"
app_title = "Dantist App"
app_publisher = "OpenedClosed"
app_description = "dantist_admin"
app_email = "opendoor200179@gmail.com"
app_license = "mit"

# Apps
# ------------------

# fixtures = [
#     # --- Кастомизации ядра ---
#     "Custom Field",
#     "Property Setter",
#     "Client Script",
#     "Server Script",
#     "Custom DocPerm",
#     "Workspace",
#     "Print Format",
#     "Report",

#     # --- Ключевые модели проекта ---
#     {"doctype": "DocType", "filters": {"name": ["in", [
#         "Bot Settings",
#         "Engagement Case",
#         "ToDo"
#     ]]}},

#     # --- Настройки ролей и прав доступа ---
#     "Role",
#     "User Group",
#     "User Group Member",
#     "User Permission",

#     # --- Канбаны и вёркспейсы (без данных задач) ---
#     "Kanban Board",
#     "Workspace Shortcut",
#     "Workspace Link",
# ]

fixtures = [
    # --- Кастомизации ядра ---
    "Custom Field",
    "Property Setter",
    "Client Script",
    "Server Script",
    "Custom DocPerm",
    "Workspace",
    "Print Format",
    "Report",

    # --- Ключевые модели проекта (оставляем выборочно через filters) ---
    {
        "doctype": "DocType",
        "filters": {
            "name": ["in", [
                "Bot Settings",
                "Engagement Case",
                "ToDo",
            ]]
        },
    },

    # --- Настройки ролей и прав доступа ---
    "Role",
    "User Group",
    "User Group Member",
    "User Permission",

    # --- Канбаны и вёркспейсы (без данных задач) ---
    "Kanban Board",
    "Workspace Shortcut",
    "Workspace Link",

    "Custom HTML Block",   # твой кастомный DocType с HTML
]

# required_apps = []

# Each item in the list will be shown as an app in the apps page
app_logo_url = "/assets/dantist_app/images/logo.svg"
add_to_apps_screen = [
	{
		"name": "dantist_app",
		"logo": "/assets/dantist_app/images/logo.svg",
		"title": "PaNa Admin",
		"route": "/app",
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_js = [
    "/assets/dantist_app/js/other/ec_board_colors.js",
    "/assets/dantist_app/js/other/ec_colors.js",  

    "/assets/dantist_app/js/hide/topbar.js",
    "/assets/dantist_app/js/hide/workspace.js",
    "/assets/dantist_app/js/hide/user_profile.js",
    "/assets/dantist_app/js/hide/global_energy.js",
    "/assets/dantist_app/js/hide/global_forms.js",
    "/assets/dantist_app/js/hide/toolbar_user_menu.js",
    "/assets/dantist_app/js/hide/form_actions_menu.js",
    "/assets/dantist_app/js/hide/toolbar_notifications.js",
    "/assets/dantist_app/js/hide/list_view.js",
    "/assets/dantist_app/js/hide/user_roles_modules.js",  
    "/assets/dantist_app/js/hide/kanban_filter.js",

    "/assets/dantist_app/js/add/engagement_case_form.js",
    "/assets/dantist_app/js/add/engagement_case_tasks.js",
    "/assets/dantist_app/js/add/engagement_case_list.js",

    "/assets/dantist_app/js/edit/kanban_skin.js",
    "/assets/dantist_app/js/edit/kanban_filters_and_search.js",

    "/assets/dantist_app/js/final/kanban_hard_reload.js",
    "/assets/dantist_app/js/edit/dnt_kanban_plus.js",
    "/assets/dantist_app/js/final/autosave.js",
]

# app_include_css = [
#     "/assets/dantist_app/css/aihub_ui_policy.css",
# ]

app_include_css = [
    "theme.bundle.css"
]

website_context = {
    "favicon": "/assets/dantist_app/images/favicon.ico",
    "splash_image": "/assets/dantist_app/images/logo.svg",
}




# include js, css files in header of web template
# web_include_css = "/assets/dantist_app/css/dantist_app.css"
# web_include_js = "/assets/dantist_app/js/dantist_app.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "dantist_app/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "dantist_app/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "dantist_app.utils.jinja_methods",
# 	"filters": "dantist_app.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "dantist_app.install.before_install"
# after_install = "dantist_app.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "dantist_app.uninstall.before_uninstall"
# after_uninstall = "dantist_app.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "dantist_app.utils.before_app_install"
# after_app_install = "dantist_app.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "dantist_app.utils.before_app_uninstall"
# after_app_uninstall = "dantist_app.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "dantist_app.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
    "User": "dantist_app.permissions.user.rules.user_permission_query_conditions",
}

has_permission = {
    "User": "dantist_app.permissions.user.rules.user_has_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
    "User": {
        "after_insert": "dantist_app.api.users_and_notifications.handlers.on_user_changed",
        "on_update":    "dantist_app.api.users_and_notifications.handlers.on_user_changed",
    },
    "Engagement Case": {
        "before_save": "dantist_app.api.engagement.handlers.set_display_name",
    }
}


# Scheduled Tasks
# ---------------

scheduler_events = {
    "cron": {
        "*/1 * * * *": [
            "dantist_app.api.tasks.tasks.scheduler_heartbeat",
            "dantist_app.api.tasks.tasks.process_due_todos",
            # "dantist_app.api.tasks.tasks.test_broadcast_todo_notifications",
        ]
    },
    # "all": ["dantist_app.api.tasks.tasks.scheduler_heartbeat"]
}

# scheduler_events = {
# 	"all": [
# 		"dantist_app.tasks.all"
# 	],
# 	"daily": [
# 		"dantist_app.tasks.daily"
# 	],
# 	"hourly": [
# 		"dantist_app.tasks.hourly"
# 	],
# 	"weekly": [
# 		"dantist_app.tasks.weekly"
# 	],
# 	"monthly": [
# 		"dantist_app.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "dantist_app.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "dantist_app.event.get_events"
# }

override_whitelisted_methods = {
    # "frappe.client.get_list": "dantist_app.api.engagement.handlers.get_list",
    # "frappe.client.get":      "dantist_app.api.engagement.handlers.get",

    "frappe.desk.reportview.get":       "dantist_app.api.engagement.handlers.reportview_get",
    "frappe.desk.reportview.get_count": "dantist_app.api.engagement.handlers.reportview_get_count",
    "frappe.desk.doctype.kanban_board.kanban_board.add_card": "dantist_app.api.engagement.handlers.add_card",

}

#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "dantist_app.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["dantist_app.utils.before_request"]
# after_request = ["dantist_app.utils.after_request"]

# Job Events
# ----------
# before_job = ["dantist_app.utils.before_job"]
# after_job = ["dantist_app.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"dantist_app.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

