var api_url = 'http://127.0.0.1:3322/api'
$(function() {
	init();
});

function hide_message_bar() {
    $("#message-bar").fadeOut("normal");
}
function hide_signin_box() {
    $("#signin-main").slideUp("normal");
}
function hide_confirm_box() {
	$("#confirm-main").slideUp("normal")
}
function show_message_bar(text) {
    $("#message").text(text);
    $("#message").css('display', 'inline-block')
    $("#message-bar").fadeIn("normal");
}
function rt(user, post) {
    $("#textarea").val(' RT @' + user + ': ' + $("#" + post).text()); 
    $("#textarea")[0].focus(); 
    var obj = document.getElementById("textarea");
    obj.selectionStart = 0;
    obj.selectionEnd = 0;
} 

function async_callback(func, args) {
	function callback() {
		return func(args);
	}
	return callback;
}

function init() {
	verify_access_token();
}

function init_UI(next) {
	//
	// 初始化界面, 将一些原本隐藏的东西显示出来
	//
	$("#page-container").show();
	access_state();
}

function API_call(url, param, success_func, error_func, retry_times) {
	//
	// 用GET的方式调用API函数, 带有重试
	//
    $.ajax({
        url: url + '?' + $.param(param),
        type: 'GET',
        success: function(body) { 
        	success_func(body);
        },
        error: function() {
            //
        	// 当retry_times不为0的时候出错就重试
        	//
        	if (retry_times == 0) 
        		error_func();
        	else
        	    API_call(url, param, success_func, error_func, retry_times - 1);
        }
    });
}

function API_post(kwargs) {
	//
	// 用POST的方式调用API函数, 带有重试
	//
    $.ajax({
        url: kwargs['url'] + '?' + $.param(kwargs['params']),
        type: 'POST',
        data: $.param(kwargs['post_params']),
        timeout: 30000,
        success: kwargs['success_func'],
        error: function() {
            //
        	// 当retry_times不为0的时候出错就重试
        	//
        	if (kwargs['retry_times'] == 0) 
        		kwargs['error_func']();
        	else
        	    API_post({
        	    	url: kwargs['url'], 
        	    	params: kwargs['params'], 
        	    	post_params: kwargs['post_params'],
        	    	success_func: kwargs['success_func'], 
        	    	error_func: kwargs['error_func'], 
        	    	retry_times: kwargs['retry_times'] - 1
        	    });
        }
    });
}

function twitter_signout() {
	hide_confirm_box();
	show_message_bar('signing out ...');
	var access_token = $.cookie('access_token')
	if (access_token == null)
		return false;
	
	var param = {
		access_token: access_token
	};
	API_call(
			'/api/remove_twitter_access_token',
			param,
			function(body) {
				hide_message_bar();
				access_state();
			},
			function() {
				show_message_bar("Oops! twitter signin failed!");
			},
			3
			);	
	return false;
}

function twitter_signin() {
	hide_signin_box();
	show_message_bar('signing in ...');
	var access_token = $.cookie('access_token')
	if (access_token == null)
		return false;
	
	var param = {
		access_token: access_token,
		user: $('#user').val(),
		passwd: $('#passwd').val(),
	};
	API_call(
			'/twitter_api/access_token',
			param,
			function(body) {
				//
				// 登录成功就刷新状态
				//
				hide_message_bar();
				access_state();
			},
			function() {
				show_message_bar("Oops! twitter signin failed!");
			},
			3
			);	
	return false;
}

function show_signin_box(args) {
	$('#signin-name').html('Twitter');
	$("#signin-main").slideDown("normal");
	$('#signin_form').unbind();
	$('#signin_form').submit(twitter_signin);
}

function show_confirm_box(args) {
	$('#confirm-text').html(args['text']);
	$("#confirm-main").slideDown("normal");
	$('#confirm-ok').unbind();
	$('#confirm-ok').click(args['callback']);
}

function access_state(next) {
	//
	// 验证cookies里面的access_token是否有效
	//
	var access_token = $.cookie('access_token')
	if (access_token == null)
		return false;
	
	var param = {
		access_token: access_token
	};
	API_call(
		'/api/access_state',
		param,
		function(body) {
			state = JSON.parse(body);
			
			$('#twitter-icon').unbind();
			if (state['twitter'] == true) {
				$('#twitter-icon').attr('src', 'static/twitter-on.gif');
				get_timeline('twitter');
				$('body').everyTime('60s', 'get_timeline_twitter', async_callback(get_timeline, 'twitter'));
				$('#twitter-icon').bind('click', async_callback(show_confirm_box, {
					text: 'Are you sure to sign out twitter?',
					callback: twitter_signout,
				}));
			} else {
				$('body').stopTime('get_timeline_twitter');
				$('#twitter-icon').attr('src', 'static/twitter-off.gif');	
				$('#twitter-icon').bind('click', show_signin_box);
			}
			
			$('#sina-icon').unbind();
			if (state['sina'] == true) {
				$('#sina-icon').attr('src', 'static/sina-on.gif');
				get_timeline('sina');
				$('body').everyTime('60s', 'get_timeline_sina', async_callback(get_timeline, 'sina'));
				$('#twitter-icon').bind('click', async_callback(show_confirm_box, {
					text: 'Are you sure to sign out sina weibo?',
					callback: sina_signout,
				}));
			} else {
				$('body').stopTime('get_timeline_sina');
				$('#twitter-icon').attr('src', 'static/twitter-off.gif');	
				$('#twitter-icon').bind('click', show_signin_box);
			}
		},
		function() {
			show_message_bar("Oops! get access state failed!");
		},
		3
		);	
}

function verify_access_token(next) {
	//
	// 验证cookies里面的access_token是否有效
	//
	var access_token = $.cookie('access_token')
	if (access_token == null)
		return false;
	var param = {
		access_token: access_token
	};
	API_call(
		'/api/vaildation',
		param,
		init_UI,
		function() {
			show_message_bar("Oops! access_token vaildation failed!");
		},
		3
		);
}
function solve(pid) {
    $.ajax({
        url: 'request.php?req=solve&pid=' + pid,
        type: 'GET',
        timeout: 5000,
        success: function(json) { 
            update();
        },
        error: function(err) {
            show_message_bar("Oops! remove timeline failed!");
        }
    });
}
function json2obj(json) {
    eval("o = " + json);
    return o;
}

var timeline_list = {};
timeline_list['twitter'] = [];
timeline_list['sina'] = [];
current_status_id = {};
current_status_id['twitter'] = 0;
current_status_id['sina'] = 0;
//
//
//
//
//
function refresh_timeline() {
	var thtml = '';
	var list = [];
	for (api in timeline_list) {
	    list = list.concat(timeline_list[api]);
	}
	list.sort(function (a, b) {return b['timestamp'] - a['timestamp']});
    for (i in list) {
	    thtml += '<div class="note">';
	    thtml += '<div class="profile-image"><img src="' + list[i]['profile_image_url'] + '" /></div>';
	    thtml += '<div class="status">'
	    thtml += '<div><span>@' + list[i]['screen_name'] + '</span><span class="note-time">' + list[i]["created_at"] + '</span><a href="#" class="note-action" onclick="rt(\'' + list[i]['screen_name'] + '\', \'post' + list[i]['pid'] +'\')">RT</a></div>';
	    thtml += '<div class="note-content"><span id="post' + list[i]['id']  + '">' + list[i]["text"] + '</span></div>';
	    thtml += '</div><div><hr /></li></div></div>';
    }
	$("#notes").html(thtml);
}

function get_timeline(api_name) {
	var access_token = $.cookie('access_token')
	var param = {
		access_token: access_token
	};	
	if (current_status_id[api_name] != 0)
		param['since_id'] = current_status_id[api_name];
		
	API_call(
		'/' + api_name + '_api/home_timeline',
		param,
		function(json) {
            res = JSON.parse(json);
            tweet_list = [];
            	
            //
            // 返回长度为0则表示没有新状态, 退出即可
            //
            if (res.length == 0)
            	return
            	
            for (i = 0; i < res.length && res[i]['id'] > current_status_id[api_name]; ++i) {
            	res[i]['timestamp'] = Date.parse(res[i]['created_at']);
            	res[i]['created_at'] = time_format(new Date(res[i]['created_at']));
            	tweet_list.push(res[i]);
            }
            timeline_list[api_name] = tweet_list.concat(timeline_list[api_name]);
            current_status_id[api_name] = timeline_list[api_name][0]['id'];
            refresh_timeline();
		},
		function() {
			show_message_bar("Oops! update timeline failed!");
		},
		3
    );
}
function new_note() {
	var access_token = $.cookie('access_token')
	if (access_token == null)
		return false;
	
	var params = {
		access_token: access_token
	};
	var post_params = {
		status: $("#textarea").val()
	};
    API_post({
    	url: '/twitter_api/update',
    	params: params,
    	post_params: post_params,
    	success_func: function () {
    		get_timeline();
    	},
    	error_func: function () {
    		show_message_bar("Oops! update status failed!");
    	},
    	retry_times: 3
    });
}


month = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];

function time_format(time) {
	//
	// 将time转换成字符串
	//
    now = new Date();
    t = new Date(time)
    delta = Math.floor((now.getTime() - t.getTime()) / 1000)
    
    if (t.getFullYear() != now.getFullYear())
        
        // 如果年份不一样，则把年份显示出来
    	
        return month[t.getMonth()] + ' ' + t.getDate().toString() + ' ' + t.getFullYear().toString();
        
        
    if (delta > 24 * 60 * 60) {
    	
        // 如果时间间隔大于1天则把日期显示出来
    	
        return month[t.getMonth()] + ' ' + t.getDate().toString();
    } else {
    	ret = '';
    	
        if (Math.floor(delta / 3600) > 0) {
            ret = ret + Math.floor((delta / 3600)).toString() + 'hr';
            delta = delta % 3600;
        } else if (Math.floor(delta / 60) > 0) {
            ret = ret + Math.floor((delta / 60)).toString() + 'min';
            delta = delta % 60;
        } else {
            ret = ret + delta.toString() + 's';
        }
            
        ret += ' ago';
        return ret;
    }
	
	
}
