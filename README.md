# ECS Restart Task

## 正常重启
使用ECS Service的Schedule，借助ECS [UpdateService](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_UpdateService.html) API，指定force-new-deployment的方式对task进行重启，执行后ECS Service Scheduler会通过Service所有配置Deployment的方式，例如Rolling Update，对Task进行批量重启。

>**在Service Deployment Configuration中有两个参数: minimumHealthyPercent和maximumPercent**
>
> - maximumPercent：在Service进行RollingUpdate时，所有Task的最大数量，相对Desired Count的百分比（向下取整），包括pending和running状态的task。默认为200，最小100，即先创建和DesiredCount同样数量的新Task，再Stop旧的Task。
>
> - minimumHealthyPercent：在在Service进行RollingUpdate时，所有Healthy Task的最小数量，相对Desired Count的百分比（向上取整），只包括Running状态的Task。默认为100，最小为0，即在Service中永远保持DesiredCount数量的RunningTask。
>
> - 当maximumPercent > 100时，maximumPercent优先，即始终会先创建新的Task，而maximumPercent的值也决定了RollingUpdate的BatchSize，例如maximumPercent为150，DesiredCount为10，则在RollingUpdate时，会先一次性创建 10 * 150% - 10 = 5个Task，并进入healthy了之后，然后开始Drain同样数量旧的Task（如果有ELB的话）
>
> - 当maximumPercent = 100时，则minimumHealthyPercent决定了RollingUpdate的BatchSize，例如minimumHealthyPercent为50，DesiredCount为10，则在RollingUpdate时，会先一次性对10 - 10 * 50% = 5个task进行draining操作（如果有ELB的话），Draining结束执行StopTask，在Task被Stop了之后，才会创建同样数量的新Task，并等新的Task进入healthly之后，然后再执行下一个Update batch。
>
> - 极端情况，当minimumHealthyPercent=0，maximumPercent=100时，则会一次性Drain所有的Task，Draining结束后StopTask，然后再一次性创建所有的Task
>
> - MaximumPercent和minimumHealthyPercent不能同时设置成100，因为这会阻止Roll update
>
> - **建议maximumPercent设置为200，或者在force-new-deployment之前，先将maximumPercent修改为200**
>
```
##ECS UpdateService API Request
{
   "capacityProviderStrategy": [ 
      { 
         "base": number,
         "capacityProvider": "string",
         "weight": number
      }
   ],
   "cluster": "string",
   "deploymentConfiguration": { 
      "deploymentCircuitBreaker": { 
         "enable": boolean,
         "rollback": boolean
      },
      "maximumPercent": number,
      "minimumHealthyPercent": number
   },
   "desiredCount": number,
   "forceNewDeployment": boolean,
   "healthCheckGracePeriodSeconds": number,
   "networkConfiguration": { 
      "awsvpcConfiguration": { 
         "assignPublicIp": "string",
         "securityGroups": [ "string" ],
         "subnets": [ "string" ]
      }
   },
   "placementConstraints": [ 
      { 
         "expression": "string",
         "type": "string"
      }
   ],
   "placementStrategy": [ 
      { 
         "field": "string",
         "type": "string"
      }
   ],
   "platformVersion": "string",
   "service": "string",
   "taskDefinition": "string"
}

## 指定ECS ServiceName 和 ClusterName
HXH:~ hxh$ aws ecs update-service --service test --cluster default --force-new-deployment

```

**下面是当minimumHealthyPercent=0，maximumPercent=100时，DesiredCount=5时，执行force-new-deployment，ECS Service Scheduler调度的日志。**

从日志可以看到，先一次性deregister所有的task，并开始Draining，Draining结束后StopTask，然后再创建新的Task，加入到ELB的TargetGroup中
```
2020-12-17 22:19:56 +0800   service test deregistered 5 targets in target-group ecs-defaul-test1
2020-12-17 22:19:56 +0800   service test has begun draining connections on 5 tasks.
2020-12-17 22:25:06 +0800   service test has stopped 5 running tasks: 
2020-12-17 22:25:26 +0800   service test has started 5 tasks: 
2020-12-17 22:25:58 +0800   service test registered 3 targets in target-group ecs-defaul-test1
2020-12-17 22:26:08 +0800   service test registered 2 targets in target-group ecs-defaul-test1
2020-12-17 22:26:18 +0800   service test (deployment ecs-svc/0458381663513047547) deployment completed.
2020-12-17 22:26:18 +0800   service test has reached a steady state.
```

**下面是当minimumHealthyPercent=50，maximumPercent=100时，DesiredCount=5时，执行force-new-deployment，ECS Service Scheduler调度的日志.**

从日志可以看到，先deregisterTask，batchSize为5-5*50%=2（向上取整），并开始Draining，Draining结束后StopTask，然后再创建新BatchSize数量的Task，加入到ELB的TargetGroup中，然后再进行下一个Batch（2个task）的更新。
```
2020-12-17 22:31:34 +0800   service test deregistered 2 targets in target-group ecs-defaul-test1            ## 1st batch start
2020-12-17 22:31:34 +0800   service test has begun draining connections on 2 tasks.
2020-12-17 22:36:39 +0800   service test has stopped 2 running tasks: 
2020-12-17 22:37:10 +0800   service test has started 2 tasks: 
2020-12-17 22:37:51 +0800   service test registered 2 targets in target-group ecs-defaul-test1
2020-12-17 22:38:31 +0800   service test deregistered 2 targets in target-group ecs-defaul-test1            ## 2nd batch start
2020-12-17 22:38:31 +0800   service test has begun draining connections on 2 tasks.
2020-12-17 22:43:37 +0800   service test has stopped 2 running tasks: 
2020-12-17 22:44:07 +0800   service test has started 2 tasks: 
2020-12-17 22:44:37 +0800   service test registered 2 targets in target-group ecs-defaul-test1
2020-12-17 22:45:16 +0800   service test deregistered 1 targets in target-group ecs-defaul-test1            ## 3rd batch start
2020-12-17 22:45:16 +0800   service test has begun draining connections on 1 tasks  
2020-12-17 22:50:20 +0800   service test has stopped 1 running tasks: 
2020-12-17 22:50:40 +0800   service test has started 1 tasks: 
2020-12-17 22:51:22 +0800   service test registered 1 targets in target-group ecs-defaul-test1
2020-12-17 22:51:41 +0800   service test (deployment ecs-svc/6729443209207416664) deployment completed.
2020-12-17 22:51:41 +0800   service test has reached a steady state.

```

## 快速重启

在一些特定情况下，可能需要尽快的重启Service中所有的Task，而不需要等待Draining Timeout，并可以接受流量中断。

这种情况下，无法使用UpdateService的时候进行Task更新，因为通过Service API，不管是force-new-deployment，还是set desiredCount=0，都会被Service Scheduler调度，而先进入Connection Draining的状态。

所以只能
1. 先通过[ListTasks](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_ListTasks.html) API，列出所有的TaskARN
2. 然后对每个Task执行[StopTask](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_StopTask.html) API，去强制停止Task，这样Task会被立即终止
3. 在ELB上，会显示Target进入Draining状态，但实际上Task已经不存在，业务流量会立即中断，然后Service Scheduler会发现Task数量与DesiredCount不符，自动创建新的Task。
```
##ECS ListTasks API Request
{
   "cluster": "string",
   "containerInstance": "string",
   "desiredStatus": "string",
   "family": "string",
   "launchType": "string",
   "maxResults": number,
   "nextToken": "string",
   "serviceName": "string",
   "startedBy": "string"
}

##ECS StopTasks API Request
{
   "cluster": "string",
   "reason": "string",
   "task": "string"
}
``` 
>**需要注意：** 
>
> - ListTasks API 一次最多只能返回100个TaskARN，如果Service中有超过100个Task，在一次ListTasks API之后，如果有Task没有被返回，则在前一次ListTasks的API Response中会自动包含nextToken字段
>
> - 在下一次ListTasks，API中需要指定nextToken，会从上一次ListTasks返回结果的位置开始，再继续返回下面的Task
>
> - 如果ListTasks已返回所有的Task，则API Response中不会包含nextToken字段
>

API参考示例如下：
```
import boto3

ecs = boto3.client('ecs')
tasklist = []

##执行第一次ListTasks，不能带nextToken
taskresponse = ecs.list_tasks(
    cluster = 'default',
    serviceName = 'test',
    #maxResults = 2,
)
tasklist += taskresponse['taskArns']

##判断API返回是否有nextToken字段，如果有则继续执行ListTasks，并带上nextToken
while ('nextToken' in taskresponse):
    # print('token exist')
    taskresponse = ecs.list_tasks(
        cluster = 'default',
        serviceName = 'test',
        #maxResults = 2,
        nextToken = taskresponse['nextToken']
    )
    tasklist += taskresponse['taskArns']

##Stop所有Task
for t in tasklist:
    ecs.stop_task(
        task = t
    )
    print(t + ' being stopped')

```

## 回滚和更新

如果想要让所有的Task回滚到某一个特定的Task version，需要先执行[UpdateService](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_UpdateService.html) API，指定需要回滚的Task Definition，然后再参照上面两个章节，执行Task重启的动作。

对于进行普通回滚或更新时，修改TaskDefinition和force-new-deployment两个动作，可以同时包含在一个UpdateService API请求。

ECS将会使用新的TaskDefinition启动新的Task。

```
aws ecs update-service --service test --task-definition ‘new-task-definition' --force-new-deployment

```

对于需要快速回滚或更新Service时：
1. 执行UpdateService API，修改TaskDefinition
2. 执行ListTasks API，获取所有的TaskARN
3. 执行StopTask API，手动停止所有的Task
4. ECS Service会自动用新的TaskDefinition，启动新的Task
