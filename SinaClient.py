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

class SinaMixin(tornado.auth.OAuthMixin, tornado.web.RequestHandler):
    
    _OAUTH_REQUEST_TOKEN_URL = "http://api.t.sina.com.cn/oauth/request_token"
    _OAUTH_ACCESS_TOKEN_URL = "http://api.t.sina.com.cn/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "http://api.t.sina.com.cn/oauth/authorize"
    _OAUTH_AUTHENTICATE_URL = "http://api.t.sina.com.cn/oauth/authorize"
    _OAUTH_NO_CALLBACKS = False

    def authenticate_redirect(self):
        """Just like authorize_redirect(), but auto-redirects if authorized.

        This is generally the right interface to use if you are using
        Twitter for single-sign on.
        """
        http = tornado.httpclient.AsyncHTTPClient()
        http.fetch(self._oauth_request_token_url(callback_uri = '/sina_api/access_token'), self.async_callback(
            self._on_request_token, self._OAUTH_AUTHENTICATE_URL, None))
        
    def _on_twitter_request(self, callback, response):
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                            response.request.url)
            callback(None)
            return
        callback(tornado.escape.json_decode(response.body))
        
    def sina_request(self, path, callback, access_token=None,
                           post_args=None, **args):

        url = "http://api.t.sina.com.cn" + path + ".json"
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
        self.require_setting("sina_consumer_key", "Sina OAuth")
        self.require_setting("sina_consumer_secret", "Sina OAuth")
        return dict(
            key=self.settings["sina_consumer_key"],
            secret=self.settings["sina_consumer_secret"])

    def _oauth_get_user(self, access_token, callback):
        callback = self.async_callback(self._parse_user_response, callback)
        self.sina_request(
            "/users/show/" + access_token["user_id"],
            access_token=access_token, callback=callback)

    def _parse_user_response(self, callback, user):
        if user:
            user["username"] = user["name"]
        callback(user)
        
    @tornado.web.asynchronous    
    def get(self):
        if self.get_argument('oauth_token', None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return 
        self.authenticate_redirect()
        
class SinaSignInHanhler(SinaMixin, tornado.web.RequestHandler):
        
    def _on_auth(self, user):
        user_access_token = self.get_cookie('access_token')
        access_token = {}
        access_token = user['access_token']
        access_token['screen_name'] = user['name']
        json_at = tornado.escape.json_encode(access_token)
        db = DB()
        db.update_api_access_token('sina', user_access_token, json_at)
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
class SinaClient(SinaMixin, tornado.web.RequestHandler):
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
        t['name'] = tweet['user']['name']
        t['screen_name'] = tweet['user']['screen_name']
        t['created_at'] = tweet['created_at'].replace('+0000', 'UTC')
        t['id'] = str(tweet['id'])
        if 'retweeted_status' in tweet:
            t['in_reply_to_status_id'] = str(tweet['retweeted_status']['id'])
        else:
            t['in_reply_to_status_id'] = None
        t['profile_image_url'] = tweet['user']['profile_image_url']
        t['from'] = 'Sina'
        return t
    
    
    def _on_fetch(self, tweets, single_tweet = False):
        
        # 重载_on_twitter_request方法以后错误被拦截了，以下代码就不需要了
        # if tweets == None:
        #    raise tornado.httpclient.HTTPError(403)
        
        if single_tweet == False:
            dump = [self._dumpTweet(tweet) for tweet in tweets]
        else:
            dump = self._dumpTweet(tweets)
        self.write(tornado.escape.json_encode(dump))
        self.finish()
        
    def _on_related_results(self, res):
        
        # 处理/related_results/show/:id.json API返回结果
        # 如果有相关结果list就有1个元素 反之则没有
        
        in_reply_to = []
        replies = []
            
        if 'retweeted_status' in res:
            in_reply_to.append(self._dumpTweet(res['retweeted_status']))
        
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
                db.get_api_access_token('sina', self.get_argument('access_token'))
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
            
            self.sina_request(
                path = "/statuses/home_timeline",
                access_token = {u'secret': secret, u'key': key},
                callback = self._on_fetch,
                count = 50,
                **kwargs
                )  
        elif request == 'mentions':
            # 得到mention一个用户的Tweet

            self.sina_request(
                path = "/statuses/mentions",
                page = self.get_argument('page', 1),
                access_token = {u'secret': secret, u'key': key},
                callback = self._on_fetch,
                count = 50,
                )  
        elif request == 'show':
            #得到某个特定id的Tweet

            self.sina_request(
                path = "/statuses/show/" + str(self.get_argument('id')),
                access_token = {u'secret': secret, u'key': key},
                callback = self.async_callback(self._on_fetch, single_tweet = True),
                ) 
        elif request == 'related_results':
            
            #得到某个特定id的Tweet相关的结果

            self.sina_request(
                path = "/statuses/show/" + str(self.get_argument('id')),
                access_token = {u'secret': secret, u'key': key},
                callback = self._on_related_results,
                ) 
            
        elif request == 'user_info':
            
            # 得到某个用户的信息
            
            self.twitter_request(
                path = "/users/show",
                access_token = {u'secret': secret, u'key': key},
                callback = self._on_user_info,
                screen_name = self.get_argument('screen_name')
                )             
            
        elif request == 'remove':
            # 删除某个Tweet
            def on_fetch(tweet):
                pass
            
            self.twitter_request(
                path = "/statuses/destroy/" + str(self.get_argument('id')),
                access_token = {u'secret': secret, u'key': key},
                post_args = {},
                callback = None,
                ) 
        elif request == 'user_timeline':
            # 得到某用户的Timeline
            
            self.twitter_request(
                path = "/statuses/user_timeline",
                access_token = {u'secret': secret, u'key': key},
                page = self.get_argument('page', 1),
                screen_name = self.get_argument('screen_name'),
                callback = self._on_fetch,
                ) 
            
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
                db.get_twitter_access_token(self.get_argument('access_token'))
                )
        except:
            raise tornado.web.HTTPError(403)
        
        secret = access_token['secret']
        key = access_token['key']
        if request == 'update':
            # tweet
            
            status = tornado.escape.url_unescape(self.get_argument('status').encode('utf-8'))
            def on_fetch(tweets):
                if tweets == None:
                    raise tornado.httpclient.HTTPError(403)
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
            
            self.twitter_request(
                path = "/statuses/update",
                post_args={"status": text},
                access_token = {u'secret': secret, u'key': key},
                callback = on_fetch,
                **in_reply_to_param
                )       
            
    
