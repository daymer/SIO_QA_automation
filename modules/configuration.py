import pathlib


class SIOconfiguration:
    def __init__(self):
        self.mdm_ip = '10.234.210.22'
        self.admin_username = 'admin'
        self.admin_password = 'Scaleio123'
        self.server_user = 'root'
        self.server_password = 'password'
        self.user_session_hard_timeout_secs = 2592000
        self.user_session_timeout_secs = 2592000


class Integration:
    def __init__(self):
        self.log_location = pathlib.Path(__file__).parent

