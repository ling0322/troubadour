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
	$("#confirm-main").slideUp("normal");
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

function api_signout(api) {
	hide_confirm_box();
	show_message_bar('Signing out ...');
	var access_token = $.cookie('access_token')
	if (access_token == null)
		return false;
	
	var param = {
		access_token: access_token,
	};
	API_call(
			'/' + api + '_api/signout',
			param,
			function(body) {
				hide_message_bar();
				access_state();
			},
			function() {
				show_message_bar("Oops! " + api  + " signout failed!");
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
	$('#signin-name').html(args['api']);
    if (args['direct_signin'] == true) {
    	$('#direct-signin').show();
    	$('#goto-signin').hide();
    } else {
    	$('#direct-signin').hide();
    	$('#goto-signin').show();    	
    }
	$("#signin-main").slideDown("normal");
	$('#signin_form').unbind();
	$('#signin_form').submit(args['callback']);
}

function show_confirm_box(args) {
	$('#confirm-text').html(args['text']);
	$("#confirm-main").slideDown("normal");
	$('#confirm-ok').unbind();
	$('#confirm-ok').click(args['callback']);
}

function goto_sina_signin_page() {
	window.location.href='sina_api/access_token';
	return false;
}


var access_api = {};
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
			access_api = state;
			//
			// 先把所有的定时器移除掉
			//
			$('body').stopTime('get_timeline_twitter');
			$('body').stopTime('get_timeline_sina');
			$('#twitter-icon').unbind();
			if (state['twitter'] == true) {
				$('#twitter-icon').attr('src', 'static/twitter-on.gif');
				get_timeline('twitter', true);
				$('body').everyTime('60s', 'get_timeline_twitter', async_callback(get_timeline, 'twitter'));
				$('#twitter-icon').bind('click', async_callback(show_confirm_box, {
					text: 'Are you sure to sign out twitter?',
					callback: async_callback(api_signout, 'twitter'),
				}));
			} else {
				$('body').stopTime('get_timeline_twitter');
				$('#twitter-icon').attr('src', 'static/twitter-off.gif');	
				$('#twitter-icon').bind('click', async_callback(show_signin_box, {
					api: 'Twitter',
					direct_signin: true,
					callback: twitter_signin
				}));
			}
			
			$('#sina-icon').unbind();
			if (state['sina'] == true) {
				$('#sina-icon').attr('src', 'static/sina-on.gif');
				get_timeline('sina', true);
				$('body').everyTime('60s', 'get_timeline_sina', async_callback(get_timeline, 'sina'));
				$('#sina-icon').bind('click', async_callback(show_confirm_box, {
					text: 'Are you sure to sign out sina weibo?',
					callback: async_callback(api_signout, 'sina'),
				}));
			} else {
				$('body').stopTime('get_timeline_sina');
				$('#sina-icon').attr('src', 'static/sina-off.gif');	
				$('#sina-icon').bind('click', async_callback(show_signin_box, {
					api: 'Sina',
					direct_signin: false,
					callback: goto_sina_signin_page					
				}));
			}
			
			$('#qq-icon').unbind();
			if (state['qq'] == true) {
				$('#qq-icon').attr('src', 'static/qq-on.png');
				get_timeline('qq', true);
				$('body').everyTime('60s', 'get_timeline_qq', async_callback(get_timeline, 'qq'));
				$('#qq-icon').bind('click', async_callback(show_confirm_box, {
					text: 'Are you sure to sign out Tencent weibo?',
					callback: async_callback(api_signout, 'qq'),
				}));
			} else {
				$('body').stopTime('get_timeline_qq');
				$('#qq-icon').attr('src', 'static/qq-off.png');	
				$('#qq-icon').bind('click', async_callback(show_signin_box, {
					api: 'QQ',
					direct_signin: false,
					callback: function () {
						window.location.href='qq_api/access_token';
						return false;
					},				
				}));
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

function get_list() {
	if (content == 'Timeline') {
		return timeline_list;
	} else if (content == 'Mentions') {
		return mentions_list;
	}
}

function get_current_sid() {
	if (content == 'Timeline') {
		return current_status_id;
	} else {
		return current_mentions_id;
	}
}

var content = 'Timeline';
var timeline_list = {
	twitter: [],
	sina: [],
	qq: [],
};
var current_status_id = {
	twitter: 0,
	sina: 0,
	qq: 0,
};
var mentions_list = {
	twitter: [],
	sina: [],
	qq: [],
};
var current_mentions_id = {
	twitter: 0,
	sina: 0,
	qq: 0,
};

function content_switch(con) {
	$('#page-name').text(con);
	content = con;
	$("#new-message").hide();
	refresh_timeline();
	access_state();
}

function related_results(from, id) {
	$("#d" + id.toString()).html('<img src="static/loading.gif" />');
	if (from == 'Sina') {
		api_url = '/sina_api/related_results';
	} else if (from == 'Twitter') {
		api_url = '/twitter_api/related_results';
	} else if (from == 'QQ') {
		api_url = '/qq_api/related_results';
	}
	
	var access_token = $.cookie('access_token')
	var params = {
		access_token: access_token,
		id: id
	};	
	API_call(
			api_url,
			params,
			function(json) {
				$("#d" + id.toString()).html('');
				related = JSON.parse(json);
				thtml = '';
				if (related['in_reply_to'].length > 0) {
					thtml += '<div>---- in reply to &darr; ----</div>'
					list = related['in_reply_to'];
					for (i in list) {
						thtml += '<div>@'+ list[i]['screen_name'] +'<a href="#" class="note-action" onclick="rt(\'' + list[i]['screen_name'] + '\', \'p' + list[i]['id'] +'\')">RT</a></div>';
						thtml += '<div id="p' + list[i]['id']  + '">'+ list[i]['text'] +'</div>';
						thtml += '<div class="status-foot">'+ time_format(list[i]["created_at"]) +'</div>';
					}
					
				}
				if (related['replies'].length > 0) {
					thtml += '<div>---- replies &darr; ----</div>'
					list = related['replies'];
					for (i in list) {
						thtml += '<div>@'+ list[i]['screen_name'] +'<a href="#" class="note-action" onclick="rt(\'' + list[i]['screen_name'] + '\', \'p' + list[i]['id'] +'\')">RT</a></div>';
						thtml += '<div id="p' + list[i]['id']  + '">'+ list[i]['text'] +'</div>';
						thtml += '<div class="status-foot">'+ time_format(list[i]["created_at"]) +'</div>';
					}
					
				}
				$("#d" + id.toString()).html(thtml);
			},
			function() {
				show_message_bar("Oops! Get related result failed!");
				$("#d" + id.toString()).html('');$("#d" + id.toString()).html('');
			},
			3
			);
}

// 
//
//
//
//
function refresh_timeline() {
	var thtml = '';
	var list = [];
	var timeline_list = get_list();
	for (api in timeline_list) {
	    list = list.concat(timeline_list[api]);
	}
	list.sort(function (a, b) {return b['timestamp'] - a['timestamp']});
    for (i in list) {
	    thtml += '<div class="note">';
	    thtml += '  <div class="profile-image"><img src="' + list[i]['profile_image_url'] + '" /></div>';
	    thtml += '  <div class="status">'
	    thtml += '    <div>';
	    thtml += '      <span>@' + list[i]['screen_name'] + '</span>';
	    thtml += '      <a href="javascript: void(0)" class="note-action" onclick="rt(\'' + list[i]['screen_name'] + '\', \'p' + list[i]['id'] +'\')">RT</a>';
	    if (list[i]['in_reply_to_status_id'])
	        thtml += '      <a href="javascript: void(0)" class="note-action" onclick="related_results(\'' + list[i]['from'] + '\', \'' + list[i]['id'] + '\')">Related</a>';
	    thtml += '    </div>';
	    thtml += '    <div class="note-content"><span id="p' + list[i]['id']  + '">' + list[i]["text"] + '</span></div>';
	    thtml += '    <div>'
	    thtml += '	    <span class="status-foot">' + time_format(list[i]["created_at"]) + '</span>'
	    thtml += '	    <span class="status-foot">From</span>'
	    thtml += '	    <span class="status-foot">' + list[i]['from'] + '</span>'
	    thtml += '	  </div>';
	    thtml += '	  <div id="d' + list[i]['id']  + '">';
	    thtml += '	  </div>';
	    thtml += '  </div>';
	    thtml += '  <div><hr /></div>';
	    thtml += '</div>';
    }
	$("#notes").html(thtml);
	$("#new-message-number").text('');
	$("#new-message").fadeOut('normal');
}

var get_timeline_lock = {
	sina: {
		Timeline: false,
		Mentions: false
	},
	twitter: {
		Timeline: false,
	    Mentions: false
	},
	qq: {
		Timeline: false,
	    Mentions: false
	},
}

function strint_isgrt(a, b) {
	//
	// 这个是两个字符串型数字比较的函数 默认假设a和b都是非零数字开头的字符串
	// 且不包含其他非阿拉伯数字字符
	//
	
	
	if (a.length > b.length) {
		return true;
	} else if (a.length < b.length) {
		return false;
	} else {
		return a > b;
	}
}

function get_timeline(api_name, refresh_tl) {
	var sid = get_current_sid();
	var tl = get_list();
	var access_token = $.cookie('access_token')
	var param = {
		access_token: access_token
	};	
	var con = content;
	//
	// 如果有一个api请求进来的时候正好有一个同样的api的请求正在被执行则
	// 放弃执行这个API请求
	//
	if (get_timeline_lock[api_name][con] == true)
		return ;
	get_timeline_lock[api_name][con] = true;
	
	if (sid[api_name] != 0)
		param['since_id'] = sid[api_name];
	
	if (con == 'Timeline') {
		request = 'home_timeline';
	} else if (con == 'Mentions') {
		request = 'mentions';
	}
	API_call(
		'/' + api_name + '_api/' + request,
		param,
		function(json) {
            res = JSON.parse(json);
            tweet_list = [];
            	
            //
            // 返回长度为0则表示没有新状态, 退出即可
            //
            if (res.length == 0) {
            	get_timeline_lock[api_name][con] = false;
            	return ;
            }
            	
            var c = 0;
            for (i = 0; i < res.length && strint_isgrt(res[i]['id'], sid[api_name]); ++i) {
            	res[i]['timestamp'] = Date.parse(res[i]['created_at']);
            	tweet_list.push(res[i]);
            	c++;
            }
            tl[api_name] = tweet_list.concat(tl[api_name]);
            sid[api_name] = tl[api_name][0]['id'];
            //
            // 显示新的消息数目
            //
            if (c != 0 && !refresh_tl) {
                if ($('#new-message-number').text() == '') {
                	$('#new-message').slideDown('normal');
                	$('#new-message-number').text(c.toString());
                } else {
                	$('#new-message-number').text((parseInt($('#new-message-number').text()) + c).toString());
                }
            }
            get_timeline_lock[api_name][con] = false;
            if (refresh_tl) {
            	refresh_timeline();
            }
		},
		function() {
			// show_message_bar("Oops! update timeline failed!");
			get_timeline_lock[api_name][con] = false;
		},
		3
    );
}

function new_note() {
	var access_token = $.cookie('access_token')
	$('#loading-icon').fadeIn('normal');
	if (access_token == null)
		return false;
	
	var params = {
		access_token: access_token
	};
	var post_params = {
		status: $("#textarea").val()
	};
	n = 0;
	for (i in access_api) {
		if (access_api[i] == false)
			continue;
		n++;
        API_post({
        	url: '/' + i + '_api/update',
        	params: params,
        	post_params: post_params,
        	success_func: async_callback(function (api_n) {
        		n--;
        		if (n == 0) {
        			$("#textarea").val('');
        			$('#loading-icon').fadeOut('normal');
        		}
        		get_timeline(api_n, true);
        	}, i),
        	error_func: function () {
        		show_message_bar("Oops! update status failed!");
        		$('#loading-icon').fadeOut('normal');
        	},
        	retry_times: 3
        });
	}
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
