<!doctype html>
<html lang="en">
<head>
  <script type="text/javascript" src="http://cdn.hcharts.cn/jquery/jquery-1.8.3.min.js"></script>
  <script type="text/javascript" src="http://cdn.hcharts.cn/highcharts/highcharts.js"></script>
  <script type="text/javascript" src="http://cdn.hcharts.cn/highcharts/exporting.js"></script>
  <script>
    //左侧Javascript代码
    //<![CDATA[
    $(function () {
    $('#container').highcharts({
        chart: {
        },
        title: {
            text: '本周消费统计',
        },
        subtitle: {
            text: '{{start_time}}--{{end_time}}'
        },
        xAxis: {
            categories: {{!categories}}
        },
        yAxis:{
            title: {
                text: '消费 (元)'
            },
        },
        tooltip: {
            formatter: function() {
                var s;
                if(this.point.name){
                  s = '' + this.point.name+ ': '+this.y + '元';
                }
                else{
                  s = ''+ this.series.name  +': '+ this.y + '元';
                }
                return s;
            }
        },
        labels: {
            items: [{
                html: '汇总',
                style: {
                    left: '60px',
                    top: '-30px',
                    color: 'black'
                }
            }]
        },
        plotOptions: {
            column: {
                pointPadding: 0.2,
                borderWidth: 0,
            },
            spline: {
                    cursor: 'pointer',
                    point:{
                        events:{
                            click:function(e){
                              window.location.href=this.series.userOptions.ownURL[this.x];
                            }
                        }
                    }
            },
            pie: {
                allowPointSelect: false,
                showInLegend: false,
                cursor: 'pointer',
                center:[100,0],
                size:100,
                dataLabels: {
                    enabled: false,
                    format: '<b>{point.name}</b>: {point.percentage:.1f} %',
                    style: {
                        color: "black",
                    }
                }
            }
        },
        series: [
        // columns charts data
        % for _type,data in columnChartsData.iteritems():
          {
            "type":"column",
            "name":"{{!columnChartsNames[_type]}}",
            "data":{{!data}},
          },
        % end 
        // line charts configs
        {
          "marker": {
            "lineWidth": 3,
          },
          "data": {{!lineChartsData}},
          "ownURL":{{!lineChartsDataUrl}},
          "type": "spline",
          "name": {{!lineChartsName}},
        },
        // pie charts configs,this.point.options.ownURL
        {
          "type": "pie",
          "data":[
          % for idx,item in enumerate(pieChartsData):
          {
            "y": {{item}},
            "name": "{{!pieChartsName[idx]}}"
          },
          %end
          ]
        }
      ]
    })
});
//]]>
  </script>
  <style type="text/css">
    p{
        text-align: center;
        color: red;
        font-size: 20px;
        font-weight: bold;
    }
    a{
        text-decoration: none;
    }
    .main{
        text-align: center;
    }
  </style>
  <title>消费统计</title>
</head>
<body>
  <div id="container" style="min-width:700px;height:400px"></div>
  <p>没错，{{username}}!, 你没看错，这就是你的消费统计！</p>
  <div class="main">
      <a href = '/page/{{prev}}'>上周</a>
      <a href = '/add'>新增记录</a>
      <!--<a href = "/month">看本月</a>-->
      <a href = "/">看本周</a>
      <!--<a href = "/year">看本年</a>-->
      <a href = "/logout">退出登录</a>
      <a href = '/page/{{next}}'>下周</a>
    </div>
</body>
</html>