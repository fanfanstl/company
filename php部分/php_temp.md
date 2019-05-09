# php知识点

```bash
创建词表：
	spider模块
		
	uiitem模块
		文件创建路径：uiitem/application/conf/dev/trade.conf.php
		仿照以前的文件去写
```

```
测试：
在spider/application/scripts中创建测试脚本
脚本中内容：
	初始化环境
	。。。
	（可以调用不同的接口）
```

```
配置路由：
	spider中的路由：spider/applicaion/conf/base/api.conf.php
	
```

# 调用接口相关函数

```
spider中接口的调用：
    $client = new BBT_Service_Client();
    $ret = $client->call("spider", "addExpressQueryTask",	['userName'=>'fan','sourceWebsite'=>"http",'taskType'=>'spider']);

uiitem中Uiitem_Spider::getShoppingConf()，-------->通过BBT_srverice_client请求默认配置

词表中数据读取：
$wt = new BBT_WordTable();
$waliConfig = $wt->getKey('trade',"zhongguo");




```



# 配置文件描述：

```
trade.php文件中
$spiderPayListr：触发python脚本加车、支付、回填配置
$chromeWebsiteList：使用Chrome浏览器进行下单

$waliList
	fullAuto：全自动加车、下单、支付
	semiAuto：半自动加车、下单、支付（遇到反爬需要人为干预）
	manual：。。。
```
