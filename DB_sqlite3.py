# -*- coding: utf-8 -*-

'''
Created on Jul 1, 2011

@author: ling0322

数据库接口模型, 定义了Troubadour的一些基本的数据库接口

'''
import sqlite3
import Singleton
import re
import uuid
import base64

class DB(Singleton.Singleton):
    '''
    数据接口, 这是使用单件模式, 通过get_instance()函数得到这个类的实例
    '''
    def __init__(self):
        self.conn = sqlite3.connect('dbsqlite3')
        self.cursor = self.conn.cursor()
        
    def _is_strange_word(self, word):
        if len(re.findall('[^A-Za-z0-9_]', word)) == 0:
            return False
        else:
            return True
    
    def verify_user(self, username, md5passwd):
        
        # 首先检查用户名和密码是否合法, 防止sql注入
        
        if self._is_strange_word(username) == True:
            return False
        if self._is_strange_word(md5passwd) == True:
            return False
        
        self.cursor.execute("select * from user where name = '{0}' and md5passwd = '{1}'".format(username, md5passwd))
        if len(self.cursor.fetchall()) > 0:
            return True
        else:
            return False
    
    def access_state(self, access_token):
        '''
        得到一个access_token能够访问的微博状态
        '''
        self.cursor.execute("""select twitter_access_token, sina_access_token, qq_access_token
                               from user 
                               where access_token = '{0}'
                               """.format(access_token))
        result = self.cursor.fetchall()
        try:
            twitter = result[0][0]
            sina = result[0][1]
            qq = result[0][2]
        except:
            return False
         
        twitter_state = False
        sina_state = False
        qq_state = False
        if twitter:
            twitter_state = True
        if sina:
            sina_state = True
        if qq:
            qq_state = True
            
        state = dict(
            twitter = twitter_state,
            sina = sina_state,
            qq = qq_state,
            )
        
        return state
    
    def verify_access_token(self, access_token):
        '''
        验证一个access_token是否有效
        '''
        
        self.cursor.execute("select * from user where access_token = '{0}'".format(access_token))
        if len(self.cursor.fetchall()) > 0:
            return True
        else:
            return False
        
    def create_user(self, username, md5passwd):
        '''
        创建用户, 创建返回True, 否则返回False
        '''
        
        # 首先检查用户名和密码是否合法, 防止sql注入
        
        if self._is_strange_word(username) == True:
            return False
        if self._is_strange_word(md5passwd) == True:
            return False       
        
        self.cursor.execute("insert into user(name, md5passwd) values('{0}', '{1}')".format(username, md5passwd)) 
        self.conn.commit()
        self.cursor.execute("select * from user where name = '{0}' and md5passwd = '{1}'".format(username, md5passwd))
        if len(self.cursor.fetchall()) > 0:
            return True
        else:
            return False
        
    def create_access_token(self, username):
        
        # 首先检查用户名和密码是否合法, 防止sql注入
        
        if self._is_strange_word(username) == True:
            return False
        
        # 首先要检查一下用户是否存在
        
        self.cursor.execute("select * from user where name = '{0}'".format(username))
        if len(self.cursor.fetchall()) == 0:
            return False 
        
        access_token = str(uuid.uuid1())
        self.cursor.execute("update user set access_token = '{0}' where name = '{1}'".format(access_token, username))
        self.conn.commit()
        return access_token
    
    
    def remove_api_access_token(self, api, access_token):
        
        self.cursor.execute("select * from user where access_token = '{0}'".format(access_token))
        if len(self.cursor.fetchall()) == 0:
            return False 
              
        self.cursor.execute("update user set {0}_access_token = NULL where access_token = '{1}'".format(api, access_token))
        self.conn.commit()
        return True        
    
    def get_api_access_token(self, api, access_token):
        
        self.cursor.execute("select {1}_access_token from user where access_token = '{0}'".format(access_token, api))
        result = self.cursor.fetchall()
        if len(result) == 1:
            return base64.decodestring(result[0][0])
        else:
            return False
        
    def update_api_access_token(self, api, access_token, api_access_token):
        
        # 首先要检查一下用户是否存在
        
        self.cursor.execute("select * from user where access_token = '{0}'".format(access_token))
        if len(self.cursor.fetchall()) == 0:
            return False 
              
        base64_token = base64.encodestring(api_access_token)
        self.cursor.execute("update user set {2}_access_token = '{0}' where access_token = '{1}'".format(base64_token, access_token, api))
        self.conn.commit()
        return True
    

        
        
        
        
        