CAMDIR = '/home/_processInstances'
ARCHDIR = '/home/_VideoArchive'
CONFIG_NAME = 'theorem.conf'
DBDIR = 'DB'
COMMAND = '/usr/bin/processInstance'
ADDITIONAL_CONFIG = 'conf.conf'
LAG = 2



TEMPLATE = """[General]
HttpPort=

[AnalysisParams]
Diff%20Threshold=18
Bg%20threshold=15
Fg%20Threshold=50
Motion%20Threshold=0.2
Total%20Threshold=0.08
Downscale%20Coeff=0.15
Experimental=false
Valid%20motion%20bin%20height=8
Use%20virtual%20date=false
DebugImageIndex=0
Debug%20objects=false
Produce%20Debug=false

Motion%20based%20analysis=false
Difference%20based%20analysis=true

[PipelineParams]

Pipeline%20Name=cam{id}
Camera%20name={name}
Input%20Stream%20Url={address}
Output%20Url=rtmp://localhost:1935/videoanalytic/cam{id}

Archive%20Path={archdir}
Database%20Path=DB/video_analytics
Output%20Stream%20Bitrate=32

Global%20Scale=1
fps={fps}
statisticPeriodDays={storage_life}
Processing%20Interval%20Sec=600
Statistic%20Interval%20Sec=600

Server%20address=127.0.0.1
Notification%20smtp%20address=
Notification%20smtp%20login=
Notification%20smtp%20password=
Notification%20start%20time=00:00:00
Notification%20syserr%20email="""
