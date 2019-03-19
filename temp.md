# temp

```
EK443138435HK
```

爬取

链接：http://shipbao.net:8888/index.php/Account/login
账号：bbt@coe.com
密码：bon123456

61290982198621044304

运行命令：scrapy crawl shipbao_buy -a taskId=336229





数据库查询：select * from spider_sku where sourceItemVersion ='456'\G;

select * from spider_item where sourceItemVersion ='456'\G;







品牌确认

货币确认

发货地

查看链接评估





设计:

sizeMap = {

'M':97,

'L',99

}



colorToSizeToPriceMap ={

colorId:{

sizeId:value,

price:value,

marketprice:value,

isOutOfStock:value

},...

}





## 3.14

```
tmallbasem天猫基类
tmall_ifam天猫例子
taobaobasenew淘宝基类
poptaobaoyeshi淘宝例子
```



脚本上线流程

配置：

供应商：spider_name

转运国家：品牌的发货地

源品牌：脚本里配置的，也可能是动态抓取出来的

棒棒糖品牌：邮件里写明的，注意确认、确认

品牌国家：邮件里有写明