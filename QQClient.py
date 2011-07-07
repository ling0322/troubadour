# -*- coding: utf-8 -*-

'''
Created on Jun 18, 2011

@author: ling0322
'''

import tornado.web
import tornado.auth
from DB_sqlite3 import DB
import urllib
from tornado import httpclient
import logging
import tornado.escape
import base64
import time
import uuid
import binascii
import datetime

class QQMixin(tornado.auth.OAuthMixin, tornado.web.RequestHandler):
    
    _OAUTH_REQUEST_TOKEN_URL = "https://open.t.qq.com/cgi-bin/request_token"
    _OAUTH_ACCESS_TOKEN_URL = "https://open.t.qq.com/cgi-bin/access_token"
    _OAUTH_AUTHORIZE_URL = "https://open.t.qq.com/cgi-bin/authorize"
    _OAUTH_AUTHENTICATE_URL = "https://open.t.qq.com/cgi-bin/authorize"
    _OAUTH_NO_CALLBACKS = False

    def authenticate_redirect(self):
        """Just like authorize_redirect(), but auto-redirects if authorized.

        This is generally the right interface to use if you are using
        Twitter for single-sign on.
        """
        http = tornado.httpclient.AsyncHTTPClient()
        http.fetch(self._oauth_request_token_url(callback_uri = '/qq_api/access_token'), self.async_callback(
            self._on_request_token, self._OAUTH_AUTHENTICATE_URL, None))
        
    def _on_twitter_request(self, callback, response):
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                            response.request.url)
            callback(None)
            return
        callback(tornado.escape.json_decode(response.body))
        
    def _oauth_request_parameters(self, url, access_token, parameters={},
                                  method="GET"):
        """Returns the OAuth parameters as a dict for the given request.

        parameters should include all POST arguments and query string arguments
        that will be sent with the request.
        """
        consumer_token = self._oauth_consumer_token()
        base_args = dict(
            oauth_consumer_key=consumer_token["key"],
            oauth_token=access_token["key"],
            oauth_signature_method="HMAC-SHA1",
            oauth_timestamp=str(int(time.time())),
            oauth_nonce=binascii.b2a_hex(uuid.uuid4().bytes),
            oauth_version="1.0",
        )
        args = {}
        args.update(base_args)
        args.update(parameters)
        signature = tornado.auth._oauth_signature(consumer_token, method, url, args,
                                                 access_token)
        base_args["oauth_signature"] = signature
        return base_args
    
    def qq_request(self, path, callback, access_token=None,
                           post_args=None, **args):

        url = 'http://open.t.qq.com/api' + path
#        self._OAUTH_VERSION = '1.0'
        if access_token:
            all_args = {}
            all_args.update(args)
            all_args.update(post_args or {})
            consumer_token = self._oauth_consumer_token()
            method = "POST" if post_args is not None else "GET"
            oauth = self._oauth_request_parameters(
                url, access_token, all_args, method=method)
            args.update(oauth)
        if args: url += "?" + urllib.urlencode(args)
        callback = self.async_callback(self._on_twitter_request, callback)
        http = httpclient.AsyncHTTPClient()
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib.urlencode(post_args),
                       callback=callback)
        else:
            http.fetch(url, callback=callback)
            
    def _oauth_consumer_token(self):
        self.require_setting("qq_consumer_key", "Sina OAuth")
        self.require_setting("qq_consumer_secret", "Sina OAuth")
        return dict(
            key=self.settings["qq_consumer_key"],
            secret=self.settings["qq_consumer_secret"])

    def _oauth_get_user(self, access_token, callback):
        callback = self.async_callback(self._parse_user_response, callback)
        self.qq_request(
            "/user/other_info",
            access_token = access_token,
            name = access_token['name'],
            format = 'json',
            callback=callback)

    def _parse_user_response(self, callback, user):
        if user:
            user["username"] = user['data']["name"]
        callback(user)
        
    @tornado.web.asynchronous    
    def get(self):
        if self.get_argument('oauth_token', None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return 
        self.authenticate_redirect()
        
class QQSignInHandler(QQMixin, tornado.web.RequestHandler):
        
    def _on_auth(self, user):
        user_access_token = self.get_cookie('access_token')
        access_token = {}
        access_token = user['access_token']
        access_token['screen_name'] = user['username']
        json_at = tornado.escape.json_encode(access_token)
        db = DB()
        db.update_api_access_token('qq', user_access_token, json_at)
        self.clear_cookie('at')
        self.redirect('/')
        pass
    
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument('oauth_token', None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        
        self.authenticate_redirect()
        
    pass
class QQClient(QQMixin, tornado.web.RequestHandler):
    '''
    A Twitter Client for Madoka frontend
    supported request:
    POST
        update
    GET
        tl
        mention
        show  (得到某个特定id的Tweet
        usertl (User Timeline
        remove
    '''
    
    def _on_twitter_request(self, callback, response):
        
        # 这个也是TwitterMixin里面的东西，重写方法来拦截错误
        if response.error:
            raise tornado.web.HTTPError(403)
            return
        
        # 如果callback为None表示不需要回调函数，就直接调用self.finish就可以了ww
        if callback != None:
            callback(tornado.escape.json_decode(response.body))
        else:
            self.finish()
            

    def _dumpTweet(self, tweet):
        ''' 整理Tweet的内容将Twitter API返回的Tweet的格式转换成本地使用的格式 '''
        
        t = {}
        t['text'] = tweet['text']
        t['name'] = tweet['name']
        t['screen_name'] = tweet['nick']
        t['created_at'] = datetime.datetime.utcfromtimestamp(tweet['timestamp']).strftime("%a %b %d %X +0000 %Y")
        t['id'] = str(tweet['id'])
        if 'source' in tweet and tweet['source']:
            t['in_reply_to_status_id'] = str(tweet['source']['id'])
        else:
            t['in_reply_to_status_id'] = None
        if tweet['head'] == "":
            t['profile_image_url'] = 'http://mat1.gtimg.com/www/mb/images/head_50.jpg'
        else:
            t['profile_image_url'] = tweet['head'] + '/50'
        t['from'] = 'QQ'
        return t
    
    
    def _on_fetch(self, tweets, single_tweet = False):
        
        # 重载_on_twitter_request方法以后错误被拦截了，以下代码就不需要了
        # if tweets == None:
        #    raise tornado.httpclient.HTTPError(403)
        
        if single_tweet == False:
            dump = [self._dumpTweet(tweet) for tweet in tweets['data']['info']]
        else:
            dump = self._dumpTweet(tweets)
        self.write(tornado.escape.json_encode(dump))
        self.finish()
        
    def _on_related_results(self, res):
        
        # 处理/related_results/show/:id.json API返回结果
        # 如果有相关结果list就有1个元素 反之则没有
        
        in_reply_to = []
        replies = []
            
        if res['data']['source']:
            in_reply_to.append(self._dumpTweet(res['data']['source']))
        
        dump = dict(
            in_reply_to = in_reply_to,
            replies = replies,
            )
        
        self.write(tornado.escape.json_encode(dump))
        self.finish()
        
    def _dump_user_info(self, user_info):
        ui = {}
        ui['id'] = user_info['id']
        ui['name'] = user_info['name']
        ui['screen_name'] = user_info['screen_name']
        ui['location'] = user_info['location']
        ui['description'] = user_info['description']
        ui['profile_image_url'] = user_info['profile_image_url']
        ui['followers_count'] = user_info['followers_count']
        ui['friends_count'] = user_info['friends_count']
        ui['created_at'] = user_info['created_at'].replace('+0000', 'UTC')
        ui['favourites_count'] = user_info['favourites_count']
        ui['following'] = user_info['following']
        ui['statuses_count'] = user_info['statuses_count']
        return ui
        
    def _on_user_info(self, user_info):
        self.write(tornado.escape.json_encode(self._dump_user_info(user_info)))
        self.finish()

    
    @tornado.web.asynchronous
    def get(self, request):
        
        db = DB()
        try: 
            access_token = tornado.escape.json_decode(
                db.get_api_access_token('qq', self.get_argument('access_token'))
                )
        except:
            raise tornado.web.HTTPError(403)
        secret = access_token['secret']
        key = access_token['key']
        
        if request == 'home_timeline':
            # get home timeline
            kwargs = {}
            if self.get_argument('since_id', None):
                kwargs['since_id'] = self.get_argument('since_id', None)
                
            if self.get_argument('page', None):
                kwargs['page'] = self.get_argument('page', None)
            
            self.qq_request(
                path = "/statuses/home_timeline",
                access_token = {u'secret': secret, u'key': key},
                callback = self._on_fetch,
                reqnum = 50,
                **kwargs
                )  
        elif request == 'mentions':
            # 得到mention一个用户的Tweet

            self.qq_request(
                path = "/statuses/mentions",
                page = self.get_argument('page', 1),
                access_token = {u'secret': secret, u'key': key},
                callback = self._on_fetch,
                count = 50,
                )  
        elif request == 'show':
            #得到某个特定id的Tweet

            self.qq_request(
                path = "/t/show/" + str(self.get_argument('id')),
                access_token = {u'secret': secret, u'key': key},
                callback = self.async_callback(self._on_fetch, single_tweet = True),
                ) 
        elif request == 'related_results':
            
            #得到某个特定id的Tweet相关的结果

            self.qq_request(
                path = "/t/show",
                access_token = {u'secret': secret, u'key': key},
                callback = self._on_related_results,
                format = 'json',
                id = self.get_argument('id'),
                ) 
            
        elif request == 'user_info':
            
            # 得到某个用户的信息
            
            self.qq_request(
                path = "/users/show",
                access_token = {u'secret': secret, u'key': key},
                callback = self._on_user_info,
                screen_name = self.get_argument('screen_name')
                )             
            
        elif request == 'remove':
            # 删除某个Tweet
            def on_fetch(tweet):
                pass
            
            self.qq_request(
                path = "/statuses/destroy/" + str(self.get_argument('id')),
                access_token = {u'secret': secret, u'key': key},
                post_args = {},
                callback = None,
                ) 
        elif request == 'user_timeline':
            # 得到某用户的Timeline
            
            self.qq_request(
                path = "/statuses/user_timeline",
                access_token = {u'secret': secret, u'key': key},
                page = self.get_argument('page', 1),
                screen_name = self.get_argument('screen_name'),
                callback = self._on_fetch,
                ) 
            
        elif request == 'signout':
            db = DB()
            if False == db.remove_api_access_token('qq', self.get_argument('access_token')):
                raise tornado.web.HTTPError(403)
            self.finish()
            
        elif request == 'test':
            self.write('喵~')
            self.finish()
             
        else:
            raise tornado.httpclient.HTTPError(403, 'Invaild Request Path ~')     
            
    @tornado.web.asynchronous
    def post(self, request):
        db = DB()
        try: 
            access_token = tornado.escape.json_decode(
                db.get_api_access_token('qq', self.get_argument('access_token'))
                )
        except:
            raise tornado.web.HTTPError(403)
        
        secret = access_token['secret']
        key = access_token['key']
        if request == 'update':
            # tweet
            
            status = tornado.escape.url_unescape(self.get_argument('status').encode('utf-8'))
            def on_fetch(tweets):
                self.write('Done ~')
                self.finish()
            
            # 将多于140个字符的部分截去
            
            if len(status) > 140:
                text = status[:136] + '...'
            else:
                text = status

            # 如果有in_reply_to参数则带上这个参数ww
            
            in_reply_to_param = {}
            if self.get_argument('in_reply_to', None):
                in_reply_to_param['in_reply_to_status_id'] = self.get_argument('in_reply_to', None)
            
            self.qq_request(
                path = "/t/add",
                post_args={"content": text},
                access_token = {u'secret': secret, u'key': key},
                clientip = '202.120.161.232',   # 这里需要伪造一个用户IP
                callback = on_fetch,
                format = 'json',
                )       
             
            
    
