import vkfm
import logging
import time

TEST_LASTFM_USER = "creeco"

def test_vk_exact(artist='Nirvana', track='drain you'):
    vkget = vkfm.VkApi()
    tracks = vkget('=%s artist:=%s' % (track, artist))
    print("tracks like %r by %r\n============"% (track, artist))
    for track in tracks:
        print(track)

def test_lastfm_similar_artists(artist='Nirvana'):
    lfm = vkfm.LastFmApi()
    for match in lfm.get_similar_artist(artist):
        print("%20r [%20r] -- %f" % (match.name, match.mbid, match.score))

def test_lastfm_similar_tags(tag='rock'):
    lfm = vkfm.LastFmApi()
    for match in lfm.get_similar_tag(tag):
        print("%20r [%20r] -- %f" % (match.name, match.mbid, match.score))

def test_lastfm_artist_albums(artist='Nirvana'):
    lfm = vkfm.LastFmApi()
    print("albums by %r\n==============" % (artist))
    for match in lfm.get_artist_albums(artist):
        print("%40r [%r] -- %f" % (match.name, match.mbid, match.score))

def test_lastfm_album_tracks(artist='Nirvana', album='Nevermind'):
    lfm = vkfm.LastFmApi()
    a = lfm.get_album_tracks(artist, album)
    print("album %r by %r\n==============" % (a.name, a.artist))
    for match in a:
        print("%40r %5r" % (match.name, match.duration))

def test_scrobbled_tracks_artist(user=TEST_LASTFM_USER, artist="Nirvana", start_time=None, end_time=None):
    lfm = vkfm.LastFmApi()
    tracks = lfm.get_scrobbled_tracks(user, artist, start_time, end_time)
    print("%r tracks, scrobbled by %r from %r till %r\n==============" % (artist, user, start_time, end_time))
    for match in tracks:
        print("%40r %5r" % (match.name, time.strftime("%Y-%m-%d %H:%M", time.localtime(match.score))))

def test_scrobbled_tracks(user=TEST_LASTFM_USER, start_time=None, end_time=None):
    lfm = vkfm.LastFmApi()
    tracks = lfm.get_scrobbled_tracks(user, start_time, end_time)
    print("tracks, scrobbled by %r from %r till %r\n==============" % (user, start_time, end_time))
    for match in tracks:
        print("%20r %20r %5r" % (match.name, match.artist, time.strftime("%Y-%m-%d %H:%M", time.localtime(match.score))))

if __name__ == "__main__":
    logging.basicConfig()
    test_vk_exact()
    test_lastfm_similar_artists()
    test_lastfm_artist_albums()
    test_lastfm_album_tracks()
    test_scrobbled_tracks_artist()
    test_scrobbled_tracks()