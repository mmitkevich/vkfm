import requests
import re
import json
from functools import partial
import logging
import xmltodict
from collections import OrderedDict
import time

VK_ACCESS_TOKEN = "fff9ef502df4bb10d9bf50dcd62170a24c69e98e4d847d9798d63dacf474b674f9a512b2b3f7e8ebf1d69"

class bunch(dict):
    def __init__(self, *args, **kwargs):
        for a in args:
            for n in a.split(' '):
                self[n] = None
        super(bunch, self).__init__(**kwargs)
        self.__dict__ = self

class Filter(bunch):
#    mods = ["artist", "year", "album"]
    def __init__(self, mods, **kwargs):
        super(Filter, self).__init__(*mods, **kwargs)
        self.mods = mods
        self._excluding = None

    @property
    def excluding(self):
        if not self._excluding:
            self._excluding = Filter(self.mods)
        return self._excluding

    def _include(self, mod, word):
        if word[0] == '-':
            self.excluding._include(mod, word[1:])
        else:
            if not self.get(mod):
                self[mod] = [word]
            else:
                self[mod].append(word)
        return self

    @classmethod
    def loads(cls, mods, query):

        words = re.compile(r" +").split(query)
        f = cls(mods)
        mod = mods[0]
        mods = mods[1:]
        for w in words:
            kv = w.split(":")
            if len(kv) > 1 and kv[0] in mods:
                mod = kv[0]
                f._include(mod, kv[1])
            else:
                f._include(mod, w)
        return f

    def any(self, dct):
        for k, v in dct.items():
            if k in self:
                filter_values = [w.upper() for w in self[k]]
                exact = False
                match1 = False
                for i, val in enumerate(filter_values):
                    if val[0] == '=':
                        exact = True
                        val = val[1:]
                        filter_values[i] = val

                    if val.upper() in v.upper():
                        match1 = True
                        break

                if not match1:
#                    print("not_included %r=%r|%r" % (k, v, filter_values))
                    return False

                if exact:
                    for w in re.compile(r" +").split(v):
                        if not w.upper() in filter_values:
#                            print("=not_included %r=%r|%r" % (k, v, filter_values))
                            return False

        return True

    def none(self, dct):
        for k, v in dct.items():
            filter_values = self.get(k)
            if filter_values:
                match1 = True
                for val in filter_values:
                    if val[0] == '"' and val[-1] == '"':
                        val = val[1:-2]
                        if v == val:
                            #print("excluded %r=%r|%r" % (k, v, filter_values))
                            return False
                    elif v.upper() in val.upper():
                        #print("excluded %r=%r|%r" % (k, v, filter_values))
                        return False
        return True

    @staticmethod
    def match_all(filters, dct):
        for f in filters:
            if not f.any(dct):
                return False
            if not f.excluding.none(dct):
                return False
        return True

class Api(object):
    logger = logging.getLogger(__name__)

    def get1(self, url, data, **kwargs):
        response = requests.get(url, params=data, **kwargs)
        if response.status_code != 200:
            return "http error %r" % response.code, response.content
        try:
            if 'json' in response.headers['content-type']:
                cont = json.loads(response.text)
            elif 'xml' in response.headers['content-type']:
                cont = xmltodict.parse(response.text)
            else:
                cont = response.text
            return None, cont
        except ValueError as e:
            return "json error %r, data:\n%r" % e, None, cont[:80]

    def error(self, request, response):
        self.__class__.logger.error("http %r" % response.code)

    def get(self, filter, **kwargs):
        raise NotImplementedError("Getter.get should be implemented in %r" % self.__class__)

    def __call__(self, *args, **kwargs):
        return self.get(args[0], **kwargs)


class TrackFilter(Filter):
    mods = ["name", "artist", "year", "album"]




class VkApi(Api):
    vk_site = bunch(
        url="https://api.vk.com/method/audio.search",
        access_token=VK_ACCESS_TOKEN
    )

    def get(self, *args, **kwargs):
        filters = [TrackFilter.loads(TrackFilter.mods, str(f)) if not isinstance(f, Filter) else f for f in args]
        site = kwargs.pop("site", VkApi.vk_site)

        query = " ".join([" ".join(f.name)+" "+" ".join(f.artist) if f.artist else " ".join(f.name) for f in filters if f.name])

        print("%r: GET %r" % (self.__class__, query))

        err, resp = self.get1(site.url, dict(
            access_token=site.access_token,
            q=query
        ))

        #print("GET %r -> %r\n%r\n" % (query, err, resp ))

        tracks = (
            v for k, v in
            [(item, bunch(artist=item.get("artist"), name=item.get("title"), duration=item.get("duration")))
                for item in resp.get("response", [0])[1:]
            ] if Filter.match_all(filters, v)
        )
        return tracks

def update_if(dst, func, **src):
    dst.update(((k, v) for k, v in src.items() if func(k,v)))
    return dst

class Match(object):
    def __init__(self, name="", artist=None, album=None, score=0., mbid=None, duration=None):
        self.score = score
        self.name = name
        self.mbid = mbid
        self.artist = artist
        self.album = album
        self.duration = duration

class MatchSet(Match, list):
    def __init__(self, iterable, name="", artist=None, album=None, score=0., mbid=None, duration=None):
        Match.__init__(self, name, artist, album, score, mbid, duration)
        list.__init__(self, iterable)

SECONDS_PER_DAY = 24*60*60

class LastFmApi(Api):
    def __init__(self):
        self.appname = "vpashamuzic"
        self.apikey = "f0552741417f09997c476cbb3841ebdb"
        self.sharedsecret="9117e9eff197e5e69bb9d98f2baeaa4c"
        self.url = "https://ws.audioscrobbler.com/2.0"

    def get_similar_artist(self, artist):
        err, resp = self.get1(self.url, dict(method="artist.getsimilar", artist=artist, api_key=self.apikey))
        similars = resp["lfm"]["similarartists"].get("artist") or []
        return sorted((Match(name=art['name'], score=float(art['match']), mbid=art['mbid']) for art in similars), key=lambda m: -m.score)

    def get_similar_tag(self, tag):
        err, resp = self.get1(self.url, dict(method="tag.getSimilar", tag=tag, api_key=self.apikey))
        similars = resp["lfm"]["similartags"].get("tag") or []
        return (Match(name=tag['name']) for tag in similars)

    def get_artist_albums(self, artist, mbid=None):
        d = dict(method="artist.getTopAlbums", artist=artist, api_key=self.apikey)
        update_if(d, lambda k, v: v is not None, mbid=mbid)
        err, resp = self.get1(self.url, d)
        albums = resp["lfm"]["topalbums"].get("album") or []
        return sorted((Match(name=art['name'], score=float(art['playcount']), mbid=art.get('mbid')) for art in albums), key=lambda m: -m.score)

    def get_album_tracks(self, artist=None, album=None, mbid=None):
        if not mbid and (not artist or not album):
            raise ValueError("need artist+album or mbid")

        d = dict(method="album.getInfo", api_key=self.apikey)
        update_if(d, lambda k, v: v is not None, mbid=mbid, album=album, artist=artist)
        err, resp = self.get1(self.url, d)
        tracks = resp["lfm"]["album"]["tracks"].get("track") or []
        return MatchSet((Match(name=t['name'], score=0., duration=int(t['duration']), mbid=t.get('mbid')) for t in tracks), name=resp['lfm']['album'].get('name'), artist=resp['lfm']['album'].get('artist'))



    def get_scrobbled_tracks(self, user, artist=None, start_time=None, end_time=None):
        if artist is not None:
            d = dict(method="user.getArtistTracks", artist=artist, user=user, api_key=self.apikey)
            update_if(d, lambda k, v: v is not None, startTimestamp=start_time, endTimestamp=end_time)
            err, resp = self.get1(self.url, d)
            tracks = resp["lfm"]["artisttracks"].get("track") or []
            return MatchSet((Match(name=t['name'], score=float(t['date'][r'@uts']), mbid=t.get('mbid')) for t in tracks), name='%r,%r,%r' % (user, start_time, end_time), artist=artist)
        else:
            d = dict(method="user.getRecentTracks", user=user, api_key=self.apikey)
            update_if(d, lambda k, v: v is not None, **{"from": start_time, "to": end_time, "limit": 200, "extended": 1})
            err, resp = self.get1(self.url, d)
            tracks = resp["lfm"]["recenttracks"].get("track") or []
            return MatchSet((Match(name=t['name'], artist=t['artist']['name'], album=t['album']['@mbid'], score=float(t['date'][r'@uts']), mbid=t.get('mbid')) for t in tracks), name='%r,%r,%r' % (user, start_time, end_time), artist=artist)


def artist_radio_by_popularity(lfm, artist):
    albums = lfm.get_artist_albums(artist)
    for album in albums:
        tracks = lfm.get_album_tracks(album)
        for track in tracks:
            yield track

def scrobbled_tracks(lfm, user):
    tracks = lfm.get_scrobbled_tracks(user)
    for track in tracks:
        yield track
