import time

from deluge_client import DelugeRPCClient


def format_time(secs):
    if secs < 60:
        time_str = '{:d}s'.format(secs)
    elif secs < 3600:
        time_str = '{:d}m {:d}s'.format(secs // 60, secs % 60)
    elif secs < 86400:
        time_str = '{:d}h {:d}m'.format(secs // 3600, secs // 60 % 60)
    elif secs < 604800:
        time_str = '{:d}d {:d}h'.format(secs // 86400, secs // 3600 % 24)
    elif secs < 31449600:
        time_str = '{:d}w {:d}d'.format(secs // 604800, secs // 86400 % 7)
    else:
        time_str = '{:d}y {:d}w'.format(secs // 31449600, secs // 604800 % 52)
    return time_str


def format_size(fsize_b, precision=1):
    if fsize_b >= 1024 ** 4:
        return '%.*f %s' % (precision, fsize_b / 1024 ** 4, 'TiB')
    elif fsize_b >= 1024 ** 3:
        return '%.*f %s' % (precision, fsize_b / 1024 ** 3, 'GiB')
    elif fsize_b >= 1024 ** 2:
        return '%.*f %s' % (precision, fsize_b / 1024 ** 2, 'MiB')
    elif fsize_b >= 1024:
        return '%.*f %s' % (precision, fsize_b / 1024, 'KiB')
    else:
        return '%d %s' % (fsize_b, 'B')


def format_speed(bps, precision=1):
    if bps < 1024 ** 2:
        return '%.*f %s' % (precision, bps / 1024, 'KiB/s')
    elif bps < 1024 ** 3:
        return '%.*f %s' % (precision, bps / 1024 ** 2, 'MiB/s')
    elif bps < 1024 ** 4:
        return '%.*f %s' % (precision, bps / 1024 ** 3, 'GiB/s')
    else:
        return '%.*f %s' % (precision, bps / 1024 ** 4, 'TiB/s')


class DelugeHelper:
    client = None

    def __init__(self, ip, port, user, password):
        self.client = DelugeRPCClient(ip, int(port), user, password)
        self.client.connect()

    def add_torrent(self, magnetlink, download_location):
        torrent_id = self.client.call('core.add_torrent_magnet', magnetlink, {'download_location': download_location,
                                                                              'prioritize_first_last_pieces': True,
                                                                              'sequential_download': True})
        time.sleep(2)
        torrent_name = str(self.client.call('core.get_torrent_status', torrent_id, ['name']).get(b'name'), 'utf-8')
        return 'Torrent %s started' % torrent_name

    def delete_torrent(self, torrent_id):
        torrent_name = str(self.client.call('core.get_torrent_status', torrent_id, ['name']).get(b'name'), 'utf-8')
        if self.client.call('core.remove_torrent', torrent_id, True):
            return 'Torrent %s was successfully deleted' % torrent_name
        else:
            return 'An error occurred while deleting %s' % torrent_name

    def get_torrents_to_delete(self):
        status_keys = ['name', 'total_size']
        results = self.client.call('core.get_torrents_status', {}, status_keys)
        message = 'Name - Size\n'
        for torrent_id, status in results.items():
            message += '%s - %s /del_%s \n' % (str(status.get(b'name'), 'utf-8'),
                                               format_size(status.get(b'total_size')), str(torrent_id).split("'")[1])
        return message

    def get_active_torrents(self):
        status_keys = ['name', 'download_payload_rate', 'progress', 'eta', 'total_size']
        results = self.client.call('core.get_torrents_status', {'state': 'Allocating'}, status_keys)
        results.update(self.client.call('core.get_torrents_status', {'state': 'Checking'}, status_keys))
        results.update(self.client.call('core.get_torrents_status', {'state': 'Downloading'}, status_keys))
        results.update(self.client.call('core.get_torrents_status', {'state': 'Error'}, status_keys))
        results.update(self.client.call('core.get_torrents_status', {'state': 'Queued'}, status_keys))
        results.update(self.client.call('core.get_torrents_status', {'state': 'Moving'}, status_keys))
        message = 'Name - Downloading speed - Progress - ETA - Size\n'
        for torrent_id, status in results.items():
            message += '%s - %s - %.1f%% - %s - %s \n' % (str(status.get(b'name'), 'utf-8'),
                                                          format_speed(status.get(b'download_payload_rate')),
                                                          status.get(b'progress'), format_time(status.get(b'eta')),
                                                          format_size(status.get(b'total_size')))
        return message

    def get_finished_torrents(self):
        status_keys = ['name', 'upload_payload_rate', 'progress', 'total_size']
        results = self.client.call('core.get_torrents_status', {'state': 'Seeding'}, status_keys)
        results.update(self.client.call('core.get_torrents_status', {'state': 'Paused'}, status_keys))
        message = 'Name - Uploading speed - Progress - Size\n'
        for torrent_id, status in results.items():
            message += '%s - %s - %.1f%% - %s \n' % (str(status.get(b'name'), 'utf-8'),
                                                     format_speed(status.get(b'upload_payload_rate')),
                                                     status.get(b'progress'), format_size(status.get(b'total_size')))
        return message
