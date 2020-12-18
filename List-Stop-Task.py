import boto3

ecs = boto3.client('ecs')
tasklist = []

taskresponse = ecs.list_tasks(
    cluster = 'default',
    serviceName = 'test',
    #maxResults = 2,
)
tasklist += taskresponse['taskArns']

while ('nextToken' in taskresponse):
    # print('token exist')
    taskresponse = ecs.list_tasks(
        cluster = 'default',
        serviceName = 'test',
        #maxResults = 2,
        nextToken = taskresponse['nextToken']
    )
    tasklist += taskresponse['taskArns']

for t in tasklist:
    ecs.stop_task(
        task = t
    )
    print(t + ' being stopped')



