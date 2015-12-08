VKFM
===========================

simple vkontakte/lastfm api mix

See test_vkfm.py for usage details.

Get last scrobbled tracks:
---------

```python

def test_scrobbled_tracks(user=TEST_LASTFM_USER, start_time=None, end_time=None):
    lfm = vkfm.LastFmApi()
    tracks = lfm.get_scrobbled_tracks(user, start_time, end_time)
    print("tracks, scrobbled by %r from %r till %r\n==============" % (user, start_time, end_time))
    for match in tracks:
        print("%20r %20r %5r" % (match.name, match.artist, time.strftime("%Y-%m-%d %H:%M", time.localtime(match.score))))


```