# -*- coding: utf-8 -*-
 
import sys 
reload(sys) 
sys.setdefaultencoding('utf-8') 


import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web 
import os.path
import TwitterClient
import SinaClient
from tornado.options import define, options
from DB_sqlite3 import DB

define("port", default=3322, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self): 
        handlers = [
            (r"/", MainHandler),
            (r"/api/(.*)", ApiHandler),
            (r"/sina_api/access_token", SinaClient.SinaSignInHanhler),
            (r"/sina_api/(.*)", SinaClient.SinaClient),
            (r"/twitter_api/access_token", TwitterClient.TwitterSignInHandler),
            (r"/twitter_api/(.*)", TwitterClient.TwitterClient),
            (r"/signin", LoginHandler),
            (r"/signup", SignUpHandler),
            (r"/logout", LogoutHandler),
        ]
        settings = dict(
            login_url = "/login",
            sina_consumer_key = "3436920788",
            sina_consumer_secret = "1591823d9615cc4687776a575b73c75a",
            twitter_consumer_key = "cFDUg6a9DU08rPQTukw2w",
            twitter_consumer_secret = "gxDykjVceNppTow1LppvXTrUWNjwIOFvhnf0Imy6NQ0",
            cookie_secret="43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            static_path = os.path.join(os.path.dirname(__file__), "static"),
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class TroubadourBaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        return self.get_cookie("access_token", None)
 
        
class MainHandler(TroubadourBaseHandler):
    # @tornado.web.authenticated
    def get(self):
        
        self.render("homura.html")

class SignUpHandler(TroubadourBaseHandler):
    def get(self):
        status = self.get_argument('status', None)
        self.render("signup.html", status = status)
    
    def post(self):
        db = DB()
        if True == db.create_user(self.get_argument('username'), self.get_argument('md5passwd')):
            self.redirect('/signin')
        else:
            self.redirect('signup?status=failed')

class LoginHandler(TroubadourBaseHandler):
    def get(self):
        status = self.get_argument('status', None)
        self.render('signin.html',  status = status)
        
    def post(self):
        username = self.get_argument('username')
        md5passwd = self.get_argument('md5passwd')
        db = DB()
        if db.verify_user(username, md5passwd) == True:
            self.set_cookie(
                'access_token', 
                db.create_access_token(username),
                expires_days = 30
                )
            self.redirect('/')
        else:
            self.redirect('/signin?status=failed')
    
class ApiHandler(tornado.web.RequestHandler):
    '''
    本地的API调用
    '''
    def get(self, request):
        if request == "vaildation":
            access_token = self.get_argument('access_token')
            db = DB()
            if False == db.verify_access_token(access_token):
                raise tornado.web.HTTPError(403)
        elif request == "access_state":
            access_token = self.get_argument('access_token')
            db = DB()
            self.write(tornado.escape.json_encode(db.access_state(access_token)))
        elif request == "remove_twitter_access_token":
            access_token = self.get_argument('access_token')
            db = DB()
            if False == db.remove_twitter_access_token(access_token):
                raise tornado.web.HTTPError(403)

class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect('/')


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
